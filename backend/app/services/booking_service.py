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
    BookingStatus,
    CheckinStatus,
    Direction,
    PaymentStatus,
    SSRStatus,
    TicketStatus,
)
from app.services import fare_service, flight_service, itinerary_service, passenger_service, payment_service, ticket_service
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
    passengers = []
    for pid in booking["passenger_ids"]:
        p = db.passengers.get(pid) or {}
        passengers.append(
            {
                "passenger_id": pid,
                "first_name": p.get("first_name", ""),
                "last_name": p.get("last_name", ""),
                "date_of_birth": p.get("date_of_birth"),
                "gender": p.get("gender", "X"),
                "passenger_type": p.get("passenger_type", "ADULT"),
            }
        )

    segments = []
    for segment in booking["segments"]:
        flight = flight_service.get_flight(segment["flight_id"])
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
        segments.append(
            {**segment, "flight": flight_service.summarize(flight, airports), "passengers": segment_passengers}
        )

    payment = db.payments.get(booking["payment_id"])
    return {
        **{k: booking[k] for k in ("booking_id", "pnr", "status", "trip_type", "user_id", "class_id", "total_amount", "currency", "created_at")},
        "contact_email": booking.get("contact_email"),
        "contact_phone": booking.get("contact_phone"),
        "cabin_name": ref.class_names().get(booking["class_id"], booking["class_id"]),
        "segments": segments,
        "passengers": passengers,
        "payment": {k: payment[k] for k in ("payment_id", "status", "amount", "currency")},
        "ssrs": db.ssrs.find(booking_id=booking["booking_id"]),
    }


# Create

def _ensure_not_double_booked(passenger_ids: list[str], flight_ids_: list[str], exclude_booking_id: str | None = None):
    for booking in db.bookings.filter(lambda b: b["status"] in ACTIVE_BOOKING_STATUSES):
        if booking["booking_id"] == exclude_booking_id or not set(flight_ids(booking)) & set(flight_ids_):
            continue
        clash = set(passenger_ids) & set(booking["passenger_ids"])
        if clash:
            raise ConflictError(f"Passenger(s) {', '.join(sorted(clash))} already booked on one of these flights ({booking['pnr']}).")


def _validate_payment(payment: dict, data, user_id: str, amount: float) -> None:
    status = PaymentStatus(payment["status"])
    if status in {PaymentStatus.REJECTED, PaymentStatus.FAILED}:
        raise BadRequestError("Payment was rejected. The booking is not confirmed and no seats were reserved.")
    if status != PaymentStatus.COMPLETED:
        raise BadRequestError(f"Payment {payment['payment_id']} is {status}; it must be COMPLETED to confirm a booking.")
    if payment["booking_id"]:
        raise ConflictError(f"Payment {payment['payment_id']} has already been used for booking {payment['booking_id']}.")
    if (
        payment["user_id"] != user_id
        or payment["outbound_flight_ids"] != data.outbound_flight_ids
        or payment["return_flight_ids"] != data.return_flight_ids
        or payment["class_id"] != data.class_id
        or sorted(payment["passenger_ids"]) != sorted(data.passenger_ids)
    ):
        raise BadRequestError("Payment does not match the requested user, flights, cabin and passengers.")
    if abs(payment["amount"] - amount) > 0.01:
        raise ConflictError(f"Fare has changed since payment (paid {payment['amount']}, current {amount}).")


def create_booking(data, actor: Principal | None) -> dict:
    """Confirm a booking against a completed payment, reserve seats on every segment and issue a PNR."""
    user_id = payment_service.resolve_user_id(data.user_id, actor)
    with transaction():
        trip = itinerary_service.prepare_trip(data.outbound_flight_ids, data.return_flight_ids, data.class_id, data.passenger_ids)
        itinerary_service.ensure_passengers_belong_to(trip["party"], user_id)
        _ensure_not_double_booked(data.passenger_ids, [f["flight_id"] for f in trip["flights"]])

        payment = payment_service.get_payment(data.payment_id, actor, data.payment_key)
        _validate_payment(payment, data, user_id, trip["quote"]["total"])

        for flight in trip["flights"]:
            fare_service.reserve_seats(flight["flight_id"], data.class_id, trip["seats"])
        booking = {
            "booking_id": next_id("BK"),
            "pnr": generate_pnr(),
            "user_id": user_id,
            "trip_type": trip["trip_type"].value,
            "segments": build_segments(data.outbound_flight_ids, data.return_flight_ids),
            "class_id": data.class_id.value,
            "passenger_ids": data.passenger_ids,
            "payment_id": payment["payment_id"],
            "total_amount": payment["amount"],
            "currency": payment["currency"],
            "status": BookingStatus.CONFIRMED.value,
            "contact_email": data.contact_email,
            "contact_phone": data.contact_phone,
            "created_at": now_iso(),
            "updated_at": None,
            "cancelled_at": None,
        }
        db.bookings.insert(booking)
        db.payments.update(payment["payment_id"], {"booking_id": booking["booking_id"], "updated_at": now_iso()})
        _record(booking["booking_id"], "CREATED", pnr=booking["pnr"], flights=flight_ids(booking))
    return build_view(booking)


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
        "currency": booking["currency"],
    }


# Cancel and delete

def _release_booking(booking: dict, timestamp: str) -> None:
    """Return seats on every segment, refund, and cancel SSRs, check-ins and tickets."""
    flights = [flight_service.get_flight(fid) for fid in flight_ids(booking)]
    party = passenger_service.validate_party(booking["passenger_ids"], date.fromisoformat(flights[0]["departure_date"]))
    for flight in flights:
        fare_service.release_seats(flight["flight_id"], booking["class_id"], fare_service.seats_required(party))
    payment_service.refund(booking["payment_id"])
    ticket_service.cancel_tickets_for_booking(booking["booking_id"])
    for checkin in db.checkins.find(booking_id=booking["booking_id"], status=CheckinStatus.CHECKED_IN.value):
        db.checkins.update(checkin["checkin_id"], {"status": CheckinStatus.NOT_CHECKED_IN.value, "updated_at": timestamp})
    for ssr in db.ssrs.find(booking_id=booking["booking_id"], status=SSRStatus.CONFIRMED.value):
        db.ssrs.update(ssr["ssr_id"], {"status": SSRStatus.CANCELLED.value, "cancelled_at": timestamp})


def cancel_booking(booking_id: str, actor: Principal | None, reason: str | None = None, last_name: str | None = None) -> dict:
    """Cancel before the first departure. The booking and PNR are kept."""
    with transaction():
        booking = get_manageable_booking(booking_id, actor, last_name)
        _require_active(booking)
        if flight_service.has_departed(flight_service.get_flight(flight_ids(booking)[0])):
            raise BadRequestError("A booking cannot be cancelled after the first flight has departed.")
        timestamp = now_iso()
        _release_booking(booking, timestamp)
        booking = db.bookings.update(
            booking_id, {"status": BookingStatus.CANCELLED.value, "cancelled_at": timestamp, "updated_at": timestamp}
        )
        _record(booking_id, "CANCELLED", reason=reason)
    return build_view(booking)


def delete_booking(booking_id: str) -> None:
    """Admin: permanently remove a booking and its check-ins, tickets, SSRs and history.

    Seats of an active booking are released and its payment refunded first; the payment record is kept for audit.
    """
    with transaction():
        booking = db.bookings.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking {booking_id} not found.")
        if booking["status"] in ACTIVE_BOOKING_STATUSES:
            _release_booking(booking, now_iso())
        for repo in (db.checkins, db.tickets, db.ssrs, db.booking_history):
            repo.remove_where(booking_id=booking_id)
        db.bookings.remove(booking_id)
