"""Bookings: creation, retrieval (PNR/booking ID + last name), journey change and cancellation.

A booking holds ordered segments. Each segment is one flight in the OUTBOUND or
RETURN journey; a journey with two segments is a connection.
"""
from datetime import date, timedelta

from app.auth.dependencies import Principal, owns
from app.config import settings
from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import (
    ACTIVE_BOOKING_STATUSES,
    HOLDING_BOOKING_STATUSES,
    BookingStatus,
    CheckinStatus,
    Direction,
    PassengerType,
    PaymentStatus,
    SSRStatus,
    TicketStatus,
)
from app.services import (
    baggage_service,
    currency_service,
    fare_service,
    flight_service,
    itinerary_service,
    passenger_service,
    payment_service,
    ticket_service,
    webhook_service,
)
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.utils.ids import generate_pnr
from app.utils.timeutils import now_iso, parse_dt, utcnow


# Segments

def build_segments(outbound_ids: list[str], return_ids: list[str]) -> list[dict]:
    legs = [(fid, Direction.OUTBOUND) for fid in outbound_ids] + [(fid, Direction.RETURN) for fid in return_ids]
    return [{"segment_no": i, "flight_id": fid, "direction": d.value} for i, (fid, d) in enumerate(legs, start=1)]


def journey_ids(booking: dict, direction: Direction) -> list[str]:
    return [s["flight_id"] for s in booking["segments"] if s["direction"] == direction]


def flight_ids(booking: dict) -> list[str]:
    return [s["flight_id"] for s in booking["segments"]]


# Access

def matches_last_name(booking: dict, last_name: str | None) -> bool:
    return passenger_service.has_last_name(booking["passenger_ids"], last_name)


def find_by_pnr(pnr: str, last_name: str) -> dict:
    """Airline convention: a PNR is only disclosed together with a matching passenger last name."""
    booking = db.bookings.find_one(pnr=pnr.strip().upper())
    if not booking or not matches_last_name(booking, last_name):
        raise NotFoundError("No booking found for this PNR and last name.")
    return booking


def get_booking(booking_id: str, actor: Principal | None, last_name: str | None = None) -> dict:
    """Owner and admins may read by booking ID; anyone else (including guests) needs a matching last name."""
    booking = db.bookings.get(booking_id)
    if not booking or not (owns(actor, booking["user_id"]) or matches_last_name(booking, last_name)):
        raise NotFoundError("No booking found for this booking ID and last name.")
    return booking


def get_manageable_booking(booking_id: str, actor: Principal | None, last_name: str | None = None) -> dict:
    """"Manage booking" access: the owner, an admin, or anyone holding a passenger's last name (guests)."""
    booking = db.bookings.get(booking_id)
    if not booking:
        raise NotFoundError(f"Booking {booking_id} not found.")
    if not (owns(actor, booking["user_id"]) or matches_last_name(booking, last_name)):
        raise ForbiddenError("Log in as the booking owner, or provide the last name of a passenger on the booking.")
    return booking


def list_bookings(
    actor: Principal, user_id: str | None = None, status: BookingStatus | None = None, pnr: str | None = None
) -> list[dict]:
    if not actor.is_admin:
        user_id = actor.user_id

    def matches(b: dict) -> bool:
        return (
            (not user_id or b["user_id"] == user_id)
            and (not status or b["status"] == status)
            and (not pnr or b["pnr"] == pnr.strip().upper())
        )

    return sorted(db.bookings.filter(matches), key=lambda b: b["booking_id"], reverse=True)


def history(booking_id: str, actor: Principal | None, last_name: str | None = None) -> list[dict]:
    get_manageable_booking(booking_id, actor, last_name)
    return sorted(db.booking_history.find(booking_id=booking_id), key=lambda h: h["history_id"])


def _record(booking_id: str, action: str, **details) -> None:
    db.booking_history.insert(
        {"history_id": next_id("BH"), "booking_id": booking_id, "action": action, "details": details, "created_at": now_iso()}
    )


# View

def infant_pairs(booking: dict, passengers: dict[str, dict] | None = None) -> dict[str, str]:
    """Map each infant to the adult whose lap they travel on.

    An explicit `accompanying_adult_id` wins; other infants are paired with the remaining adults in booking order.
    """
    passengers = passengers or {pid: db.passengers.get(pid) or {} for pid in booking["passenger_ids"]}
    adults = [pid for pid in booking["passenger_ids"] if passengers[pid].get("passenger_type") == PassengerType.ADULT]
    infants = [pid for pid in booking["passenger_ids"] if passengers[pid].get("passenger_type") == PassengerType.INFANT]
    pairs = {i: passengers[i]["accompanying_adult_id"] for i in infants if passengers[i].get("accompanying_adult_id") in adults}
    free_adults = [a for a in adults if a not in pairs.values()]
    for infant in (i for i in infants if i not in pairs):
        if free_adults:
            pairs[infant] = free_adults.pop(0)
    return pairs


def _tier_for(booking: dict) -> dict | None:
    return ref.get_user(booking["user_id"])["tier"] if booking["user_id"] else None


def build_view(booking: dict) -> dict:
    """Resolve a booking into the reusable itinerary view used by the UI."""
    airports = ref.airport_map()
    checkins = {
        (c["flight_id"], c["passenger_id"]): c
        for c in db.checkins.find(booking_id=booking["booking_id"], status=CheckinStatus.CHECKED_IN.value)
    }
    tickets = {
        (t["flight_id"], t["passenger_id"]): t
        for t in db.tickets.find(booking_id=booking["booking_id"], status=TicketStatus.ISSUED.value)
    }
    records = {pid: db.passengers.get(pid) or {} for pid in booking["passenger_ids"]}
    pairs = infant_pairs(booking, records)
    tier = _tier_for(booking)
    flights = {s["flight_id"]: flight_service.get_flight(s["flight_id"]) for s in booking["segments"]}
    domestic_by_direction = {
        d: all(ref.is_domestic(flights[s["flight_id"]]["departure_airport"], flights[s["flight_id"]]["arrival_airport"], airports)
               for s in booking["segments"] if s["direction"] == d)
        for d in {s["direction"] for s in booking["segments"]}
    }

    passengers = []
    for pid in booking["passenger_ids"]:
        p = records[pid]
        passengers.append(
            {
                "passenger_id": pid,
                "first_name": p.get("first_name", ""),
                "last_name": p.get("last_name", ""),
                "date_of_birth": p.get("date_of_birth"),
                "gender": p.get("gender", "X"),
                "passenger_type": p.get("passenger_type", "ADULT"),
                "infant_on_lap_of": pairs.get(pid),
                "baggage": {
                    d: baggage_service.allowance(domestic, booking["class_id"], p.get("passenger_type", "ADULT"), tier)
                    for d, domestic in domestic_by_direction.items()
                },
            }
        )

    segments = []
    for segment in booking["segments"]:
        flight = flights[segment["flight_id"]]
        segment_passengers = []
        for pid in booking["passenger_ids"]:
            checkin, ticket = checkins.get((flight["flight_id"], pid)), tickets.get((flight["flight_id"], pid))
            segment_passengers.append(
                {
                    "passenger_id": pid,
                    "checkin_status": CheckinStatus.CHECKED_IN if checkin else CheckinStatus.NOT_CHECKED_IN,
                    "checkin_id": checkin["checkin_id"] if checkin else None,
                    "seat": checkin["seat"] if checkin else None,
                    "ticket_status": TicketStatus.ISSUED if ticket else TicketStatus.NOT_ISSUED,
                    "ticket_id": ticket["ticket_id"] if ticket else None,
                    "ticket_number": ticket["ticket_number"] if ticket else None,
                }
            )
        segments.append({**segment, "flight": flight_service.summarize(flight, airports), "passengers": segment_passengers})

    payment = db.payments.get(booking["payment_id"]) if booking.get("payment_id") else None
    return {
        **{k: booking[k] for k in ("booking_id", "pnr", "status", "trip_type", "user_id", "class_id", "total_amount",
                                   "currency", "base_amount", "created_at")},
        "base_currency": settings.currency,
        "hold_expires_at": booking.get("hold_expires_at"),
        "contact_email": booking.get("contact_email"),
        "contact_phone": booking.get("contact_phone"),
        "cabin_name": ref.class_names().get(booking["class_id"], booking["class_id"]),
        "segments": segments,
        "passengers": passengers,
        "payment": payment and {
            "payment_id": payment["payment_id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "currency": payment["currency"],
            "card": payment["card"],
            "payment_url": payment["payment_url"] if payment["status"] == PaymentStatus.PENDING else None,
        },
        "ssrs": db.ssrs.find(booking_id=booking["booking_id"]),
    }


# Create (hold) and confirm

def resolve_user_id(requested: str | None, actor: Principal | None) -> str | None:
    """Guests book without an account; customers book for themselves; admins may book for any user."""
    if actor is None:
        if requested:
            raise ForbiddenError("Log in to book on behalf of a user account.")
        return None
    if actor.is_admin:
        user_id = requested or actor.user_id
    elif requested and requested != actor.user_id:
        raise ForbiddenError("You can only book for your own account.")
    else:
        user_id = actor.user_id
    ref.get_user(user_id)
    return user_id


def _ensure_not_double_booked(passenger_ids: list[str], flight_ids_: list[str], exclude_booking_id: str | None = None):
    for booking in db.bookings.filter(lambda b: b["status"] in HOLDING_BOOKING_STATUSES):
        if booking["booking_id"] == exclude_booking_id or not set(flight_ids(booking)) & set(flight_ids_):
            continue
        clash = set(passenger_ids) & set(booking["passenger_ids"])
        if clash:
            raise ConflictError(f"Passenger(s) {', '.join(sorted(clash))} already booked on one of these flights ({booking['pnr']}).")


def _session_options(data) -> dict:
    return {
        "client_reference_id": data.client_reference_id,
        "metadata": data.metadata,
        "success_url": data.success_url,
        "cancel_url": data.cancel_url,
    }


def _session_result(booking: dict, payment: dict) -> dict:
    return {
        "booking": build_view(booking),
        "payment": {k: payment[k] for k in ("payment_id", "session_id", "payment_url", "status", "amount", "currency",
                                            "base_amount", "base_currency", "expires_at", "client_reference_id")},
    }


def create_booking(data, actor: Principal | None) -> dict:
    """Hold seats and issue a PNR, then open a hosted payment session. Paying confirms the booking."""
    expire_holds()
    user_id = resolve_user_id(data.user_id, actor)
    currency = currency_service.validate(data.currency)
    with transaction():
        trip = itinerary_service.prepare_trip(data.outbound_flight_ids, data.return_flight_ids, data.class_id, data.passenger_ids)
        itinerary_service.ensure_passengers_belong_to(trip["party"], user_id)
        _ensure_not_double_booked(data.passenger_ids, [f["flight_id"] for f in trip["flights"]])

        for flight in trip["flights"]:
            fare_service.reserve_seats(flight["flight_id"], data.class_id, trip["seats"])
        hold_expires = utcnow() + timedelta(minutes=settings.booking_hold_minutes)
        base_amount = trip["quote"]["total"]
        booking = {
            "booking_id": next_id("BK"),
            "pnr": generate_pnr(),
            "user_id": user_id,
            "trip_type": trip["trip_type"].value,
            "segments": build_segments(data.outbound_flight_ids, data.return_flight_ids),
            "class_id": data.class_id.value,
            "passenger_ids": data.passenger_ids,
            "payment_id": None,
            "base_amount": base_amount,
            "total_amount": currency_service.convert(base_amount, currency),
            "currency": currency,
            "status": BookingStatus.PENDING.value,
            "hold_expires_at": hold_expires.isoformat(timespec="seconds"),
            "contact_email": data.contact_email,
            "contact_phone": data.contact_phone,
            "created_at": now_iso(),
            "updated_at": None,
            "cancelled_at": None,
        }
        db.bookings.insert(booking)
        payment = payment_service.create_session(booking, currency, hold_expires, trip["quote"]["lines"], _session_options(data))
        booking = db.bookings.update(booking["booking_id"], {"payment_id": payment["payment_id"]})
        _record(booking["booking_id"], "HELD", pnr=booking["pnr"], flights=flight_ids(booking), hold_expires_at=booking["hold_expires_at"])
    webhook_service.emit("booking.held", event_data(booking, payment))
    return _session_result(booking, payment)


def new_payment_session(booking_id: str, data, actor: Principal | None, last_name: str | None = None) -> dict:
    """Issue a fresh payment link for a held booking (e.g. the first one was lost or its currency should change)."""
    expire_holds()
    with transaction():
        booking = get_manageable_booking(booking_id, actor, last_name)
        if booking["status"] != BookingStatus.PENDING:
            raise ConflictError(f"Booking {booking['pnr']} is {booking['status']}; only held bookings need payment.")
        currency = currency_service.validate(data.currency or booking["currency"])
        breakdown = db.payments.get(booking["payment_id"])["breakdown"]
        payment = payment_service.create_session(
            booking, currency, parse_dt(booking["hold_expires_at"]), breakdown, _session_options(data)
        )
        booking = db.bookings.update(
            booking_id,
            {"payment_id": payment["payment_id"], "currency": currency,
             "total_amount": currency_service.convert(booking["base_amount"], currency), "updated_at": now_iso()},
        )
    return _session_result(booking, payment)


def event_data(booking: dict, payment: dict | None = None) -> dict:
    return {
        "booking_id": booking["booking_id"],
        "pnr": booking["pnr"],
        "status": booking["status"],
        "user_id": booking["user_id"],
        "amount": booking["total_amount"],
        "currency": booking["currency"],
        "payment_id": payment["payment_id"] if payment else booking.get("payment_id"),
        "payment_status": payment["status"] if payment else None,
        "client_reference_id": payment.get("client_reference_id") if payment else None,
        "metadata": payment.get("metadata", {}) if payment else {},
    }


def confirm_paid(payment: dict) -> dict:
    """Called by checkout after a successful charge: the hold becomes a confirmed booking."""
    booking = db.bookings.get(payment["booking_id"])
    booking = db.bookings.update(
        booking["booking_id"],
        {"status": BookingStatus.CONFIRMED.value, "hold_expires_at": None, "payment_id": payment["payment_id"],
         "currency": payment["currency"], "total_amount": payment["amount"], "updated_at": now_iso()},
    )
    _record(booking["booking_id"], "CONFIRMED", payment_id=payment["payment_id"], amount=payment["amount"], currency=payment["currency"])
    return booking


def expire_holds() -> int:
    """Release seats of unpaid holds past their expiry. Returns how many were expired."""
    now = utcnow()
    expired = []
    with transaction():
        for booking in db.bookings.find(status=BookingStatus.PENDING.value):
            if booking.get("hold_expires_at") and parse_dt(booking["hold_expires_at"]) <= now:
                _release_seats(booking)
                payment_service.close_open_sessions(booking["booking_id"], PaymentStatus.EXPIRED)
                expired.append(db.bookings.update(booking["booking_id"], {"status": BookingStatus.EXPIRED.value, "updated_at": now_iso()}))
                _record(booking["booking_id"], "EXPIRED")
    for booking in expired:
        webhook_service.emit("booking.expired", event_data(booking))
    return len(expired)


def _require_active(booking: dict) -> None:
    if booking["status"] not in ACTIVE_BOOKING_STATUSES:
        raise ConflictError(f"Booking {booking['pnr']} is {booking['status']}.")


def update_booking(booking_id: str, data, actor: Principal | None, last_name: str | None = None) -> dict:
    booking = get_manageable_booking(booking_id, actor, last_name)
    _require_active(booking)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise BadRequestError("No changes supplied.")
    booking = db.bookings.update(booking_id, {**changes, "updated_at": now_iso()})
    _record(booking_id, "UPDATED", **changes)
    return build_view(booking)


# Change

def change_journey(
    booking_id: str, direction: Direction, new_flight_ids: list[str], actor: Principal | None, last_name: str | None = None
) -> dict:
    """Replace the outbound or return journey with another itinerary between the same airports.

    Rules: requested more than 24h before the journey's first departure; the new
    journey departs no later than 7 days after the original; connections and the
    trip order remain valid; seats are available; nobody is checked in on it.
    """
    with transaction():
        booking = get_manageable_booking(booking_id, actor, last_name)
        _require_active(booking)
        old_ids = journey_ids(booking, direction)
        if not old_ids:
            raise BadRequestError(f"This booking has no {direction.lower()} journey.")
        old = [flight_service.get_flight(fid) for fid in old_ids]
        old_departure = parse_dt(old[0]["departure_time"])

        if utcnow() >= old_departure - timedelta(hours=settings.change_cutoff_hours):
            raise BadRequestError(f"The journey cannot be changed because departure is within {settings.change_cutoff_hours} hours.")
        if db.checkins.filter(lambda c: c["booking_id"] == booking_id and c["flight_id"] in old_ids and c["status"] == CheckinStatus.CHECKED_IN):
            raise ConflictError("The journey cannot be changed after check-in. Offload passengers first.")
        if new_flight_ids == old_ids:
            raise BadRequestError("The booking is already on these flights.")

        new = itinerary_service.load_journey(new_flight_ids)
        if (new[0]["departure_airport"], new[-1]["arrival_airport"]) != (old[0]["departure_airport"], old[-1]["arrival_airport"]):
            raise BadRequestError("The new journey must be between the same airports.")
        latest = old_departure + timedelta(days=settings.change_window_days)
        if parse_dt(new[0]["departure_time"]) > latest:
            raise BadRequestError(
                f"The new journey departs more than {settings.change_window_days} days after the original "
                f"(latest allowed departure {latest.isoformat()})."
            )

        outbound_ids = new_flight_ids if direction == Direction.OUTBOUND else journey_ids(booking, Direction.OUTBOUND)
        return_ids = new_flight_ids if direction == Direction.RETURN else journey_ids(booking, Direction.RETURN)
        itinerary_service.validate_trip(
            [flight_service.get_flight(f) for f in outbound_ids], [flight_service.get_flight(f) for f in return_ids]
        )
        _ensure_not_double_booked(booking["passenger_ids"], new_flight_ids, exclude_booking_id=booking_id)

        party = passenger_service.validate_party(
            booking["passenger_ids"], date.fromisoformat(flight_service.get_flight(outbound_ids[0])["departure_date"])
        )
        seats = fare_service.seats_required(party)
        added = [fid for fid in new_flight_ids if fid not in old_ids]
        removed = [fid for fid in old_ids if fid not in new_flight_ids]
        new_fares = [fare_service.get_fare(fid, booking["class_id"]) for fid in new_flight_ids]
        for fare in new_fares:
            if fare["flight_id"] in added:
                fare_service.ensure_seats(fare, seats)

        for fid in removed:
            fare_service.release_seats(fid, booking["class_id"], seats)
        for fid in added:
            fare_service.reserve_seats(fid, booking["class_id"], seats)
        timestamp = now_iso()
        for ssr in db.ssrs.filter(lambda s: s["booking_id"] == booking_id and s["flight_id"] in removed and s["status"] == SSRStatus.CONFIRMED):
            db.ssrs.update(ssr["ssr_id"], {"status": SSRStatus.CANCELLED.value, "cancelled_at": timestamp, "notes": "Cancelled by flight change"})

        old_fares = [fare_service.get_fare(fid, booking["class_id"]) for fid in old_ids]
        difference = round(fare_service.quote(new_fares, party)["total"] - fare_service.quote(old_fares, party)["total"], 2)
        booking = db.bookings.update(
            booking_id,
            {
                "segments": build_segments(outbound_ids, return_ids),
                "status": BookingStatus.CHANGED.value,
                "updated_at": timestamp,
            },
        )
        _record(booking_id, "JOURNEY_CHANGED", direction=direction.value, from_flights=old_ids, to_flights=new_flight_ids, fare_difference=difference)
    return {
        "booking": build_view(booking),
        "direction": direction,
        "previous_flight_ids": old_ids,
        "fare_difference": difference,
        "currency": settings.currency,
    }


# Cancel and delete

def _release_seats(booking: dict) -> None:
    flights = [flight_service.get_flight(fid) for fid in flight_ids(booking)]
    party = passenger_service.validate_party(booking["passenger_ids"], date.fromisoformat(flights[0]["departure_date"]))
    for flight in flights:
        fare_service.release_seats(flight["flight_id"], booking["class_id"], fare_service.seats_required(party))


def _release_booking(booking: dict, timestamp: str) -> None:
    """Return seats, refund or close payment, and cancel SSRs, check-ins and tickets."""
    _release_seats(booking)
    payment_service.close_open_sessions(booking["booking_id"], PaymentStatus.CANCELLED)
    payment_service.refund(booking.get("payment_id"))
    ticket_service.cancel_tickets_for_booking(booking["booking_id"])
    for checkin in db.checkins.find(booking_id=booking["booking_id"], status=CheckinStatus.CHECKED_IN.value):
        db.checkins.update(checkin["checkin_id"], {"status": CheckinStatus.NOT_CHECKED_IN.value, "updated_at": timestamp})
    for ssr in db.ssrs.find(booking_id=booking["booking_id"], status=SSRStatus.CONFIRMED.value):
        db.ssrs.update(ssr["ssr_id"], {"status": SSRStatus.CANCELLED.value, "cancelled_at": timestamp})


def cancel_booking(booking_id: str, actor: Principal | None, reason: str | None = None, last_name: str | None = None) -> dict:
    """Cancel a held or confirmed booking before its first departure. The booking and PNR are kept."""
    with transaction():
        booking = get_manageable_booking(booking_id, actor, last_name)
        if booking["status"] not in HOLDING_BOOKING_STATUSES:
            raise ConflictError(f"Booking {booking['pnr']} is {booking['status']}.")
        if flight_service.has_departed(flight_service.get_flight(flight_ids(booking)[0])):
            raise BadRequestError("A booking cannot be cancelled after the first flight has departed.")
        timestamp = now_iso()
        _release_booking(booking, timestamp)
        booking = db.bookings.update(
            booking_id, {"status": BookingStatus.CANCELLED.value, "cancelled_at": timestamp, "updated_at": timestamp}
        )
        _record(booking_id, "CANCELLED", reason=reason)
    webhook_service.emit("booking.cancelled", event_data(booking))
    return build_view(booking)


def delete_booking(booking_id: str) -> None:
    """Admin: permanently remove a booking and its check-ins, tickets, SSRs and history.

    Seats of a held or active booking are released and its payment refunded first; payment records are kept for audit.
    """
    with transaction():
        booking = db.bookings.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking {booking_id} not found.")
        if booking["status"] in HOLDING_BOOKING_STATUSES:
            _release_booking(booking, now_iso())
        for repo in (db.checkins, db.tickets, db.ssrs, db.booking_history):
            repo.remove_where(booking_id=booking_id)
        db.bookings.remove(booking_id)
