"""Online check-in by PNR + last name, per passenger and per flight segment.

- Each segment has its own window: it opens `checkin_opens_hours` before departure and closes
  `checkin_closes_minutes` before departure (defaults 48 h / 4 h). A booking with an outbound
  and a return flight is therefore checked in separately for each flight.
- Passengers can be checked in individually. The exception is an adult travelling with an infant
  on their lap: they check in together with the infant on that flight.
- Each passenger checked in on a flight gets one ticket / boarding pass for that flight.
"""
from collections.abc import Iterator
from datetime import datetime, timedelta

from app.auth.dependencies import Principal, owns
from app.config import settings
from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import (
    ACTIVE_BOOKING_STATUSES,
    CabinClass,
    CheckinStatus,
    FlightStatus,
    PassengerType,
    TicketStatus,
)
from app.services import booking_service, flight_service, ticket_service
from app.utils.errors import BadRequestError, ConflictError, NotFoundError
from app.utils.timeutils import now_iso, parse_dt, utcnow

INFANT_SEAT = "INF"
SEAT_LETTERS = {
    CabinClass.FIRST: "ACDF",
    CabinClass.BUSINESS: "ACDF",
    CabinClass.PREMIUM_ECONOMY: "ABCDEF",
    CabinClass.ECONOMY: "ABCDEFGHJK",
}
# Inclusive row ranges per cabin, sized for the largest seeded configuration.
CABIN_ROWS = {
    CabinClass.FIRST: (1, 2),
    CabinClass.BUSINESS: (3, 14),
    CabinClass.PREMIUM_ECONOMY: (15, 19),
    CabinClass.ECONOMY: (20, 60),
}


def _seat_sequence(class_id: str) -> Iterator[str]:
    cabin = CabinClass(class_id)
    first, last = CABIN_ROWS[cabin]
    for row in range(first, last + 1):
        for letter in SEAT_LETTERS[cabin]:
            yield f"{row}{letter}"


def _occupied_seats(flight_id: str) -> set[str]:
    return {c["seat"] for c in db.checkins.find(flight_id=flight_id, status=CheckinStatus.CHECKED_IN.value)}


def _next_free_seat(class_id: str, taken: set[str]) -> str:
    return next(seat for seat in _seat_sequence(class_id) if seat not in taken)


def _checked_in(booking_id: str, flight_id: str) -> set[str]:
    return {
        c["passenger_id"]
        for c in db.checkins.find(booking_id=booking_id, flight_id=flight_id, status=CheckinStatus.CHECKED_IN.value)
    }


def window(flight: dict) -> tuple[datetime, datetime]:
    departure = parse_dt(flight["departure_time"])
    return (
        departure - timedelta(hours=settings.checkin_opens_hours),
        departure - timedelta(minutes=settings.checkin_closes_minutes),
    )


def _flight_closed_reason(booking: dict, flight: dict) -> str | None:
    """Why check-in for this booking on this flight is not possible now, or None."""
    if booking["status"] not in ACTIVE_BOOKING_STATUSES:
        return f"Booking is {booking['status']}." + (" Complete payment first." if booking["status"] == "PENDING" else "")
    if flight["status"] == FlightStatus.CANCELLED:
        return "Flight has been cancelled."
    opens, closes = window(flight)
    now = utcnow()
    if now < opens:
        return f"Check-in opens {settings.checkin_opens_hours} hours before departure, at {opens.isoformat(timespec='minutes')}."
    if now > closes:
        return f"Check-in closed {_duration_text(settings.checkin_closes_minutes)} before departure."
    return None


def _duration_text(minutes: int) -> str:
    return f"{minutes // 60} hours" if minutes % 60 == 0 else f"{minutes} minutes"


def _segments_status(booking: dict) -> list[dict]:
    pairs = booking_service.infant_pairs(booking)
    lap_adults = {adult: infant for infant, adult in pairs.items()}
    result = []
    for segment in booking["segments"]:
        flight = flight_service.get_flight(segment["flight_id"])
        closed = _flight_closed_reason(booking, flight)
        done = _checked_in(booking["booking_id"], flight["flight_id"])
        opens, closes = window(flight)
        passengers = []
        for pid in booking["passenger_ids"]:
            reason = "Already checked in." if pid in done else closed
            passengers.append(
                {
                    "passenger_id": pid,
                    "checked_in": pid in done,
                    "eligible": reason is None,
                    "reason": reason,
                    "travels_with": pairs.get(pid) or lap_adults.get(pid),
                }
            )
        result.append(
            {
                "segment_no": segment["segment_no"],
                "direction": segment["direction"],
                "flight_id": flight["flight_id"],
                "flight_number": flight["flight_number"],
                "phase": flight_service.phase(flight),
                "checkin_opens_at": opens,
                "checkin_closes_at": closes,
                "open": closed is None,
                "reason": closed,
                "passengers": passengers,
            }
        )
    return result


def validate(pnr: str, last_name: str) -> dict:
    booking = booking_service.find_by_pnr(pnr, last_name)
    segments = _segments_status(booking)
    eligible = any(p["eligible"] for s in segments for p in s["passengers"])
    reasons = sorted({s["reason"] for s in segments if s["reason"]})
    return {
        "booking": booking_service.build_view(booking),
        "segments": segments,
        "can_check_in": eligible,
        "reasons": reasons,
    }


def _ensure_infant_pairs(booking: dict, flight: dict, selected: set[str], done: set[str]) -> None:
    """An infant and the adult whose lap they travel on check in together on each flight."""
    for infant, adult in booking_service.infant_pairs(booking).items():
        if infant in selected and adult not in selected | done:
            raise BadRequestError(f"Infant {infant} must be checked in together with adult {adult} on {flight['flight_number']}.")
        if adult in selected and infant not in selected | done:
            raise BadRequestError(f"Adult {adult} travels with infant {infant}; check them in together on {flight['flight_number']}.")


def check_in(data) -> dict:
    """Check in the selected passengers on the selected flights and issue boarding passes.

    Defaults: every flight whose check-in window is open, and every passenger not yet checked in on it.
    """
    booking = booking_service.find_by_pnr(data.pnr, data.last_name)
    segments = {s["flight_id"]: s for s in _segments_status(booking)}
    requested_flights = data.flight_ids or [fid for fid, s in segments.items() if s["open"]]
    if not requested_flights:
        raise ConflictError(" ".join(sorted({s["reason"] for s in segments.values() if s["reason"]})) or "No flight is open for check-in.")

    checkins = []
    with transaction():
        for fid in requested_flights:
            segment = segments.get(fid)
            if not segment:
                raise BadRequestError(f"Flight {fid} is not part of booking {booking['pnr']}.")
            if not segment["open"]:
                raise ConflictError(f"{segment['flight_number']}: {segment['reason']}")
            flight = flight_service.get_flight(fid)
            done = _checked_in(booking["booking_id"], fid)
            selected = set(data.passenger_ids or [pid for pid in booking["passenger_ids"] if pid not in done])
            unknown = selected - set(booking["passenger_ids"])
            if unknown:
                raise BadRequestError(f"Passenger(s) {', '.join(sorted(unknown))} are not on booking {booking['pnr']}.")
            already = selected & done
            if already and data.passenger_ids:
                raise ConflictError(f"Passenger(s) {', '.join(sorted(already))} already checked in on {flight['flight_number']}.")
            selected -= done
            if not selected:
                continue
            _ensure_infant_pairs(booking, flight, selected, done)

            passengers = {pid: db.passengers.get(pid) for pid in selected}
            ordered = [pid for pid in booking["passenger_ids"] if pid in selected]
            seated = [pid for pid in ordered if passengers[pid]["passenger_type"] != PassengerType.INFANT]
            infants = [pid for pid in ordered if pid not in seated]
            taken = _occupied_seats(fid)
            sequence = len(db.checkins.find(flight_id=fid))
            for pid in seated + infants:
                if pid in infants:
                    seat = INFANT_SEAT
                else:
                    seat = _next_free_seat(booking["class_id"], taken)
                    taken.add(seat)
                sequence += 1
                checkin = {
                    "checkin_id": next_id("CHK"),
                    "booking_id": booking["booking_id"],
                    "pnr": booking["pnr"],
                    "passenger_id": pid,
                    "flight_id": fid,
                    "class_id": booking["class_id"],
                    "seat": seat,
                    "sequence_number": sequence,
                    "status": CheckinStatus.CHECKED_IN.value,
                    "ticket_id": None,
                    "checked_in_at": now_iso(),
                    "updated_at": None,
                }
                db.checkins.insert(checkin)
                ticket = ticket_service.issue_ticket(checkin["checkin_id"])
                checkins.append({**checkin, "ticket_id": ticket["ticket_id"]})
    if not checkins:
        raise ConflictError("The selected passengers are already checked in on the selected flights.")

    return {
        "booking_id": booking["booking_id"],
        "pnr": booking["pnr"],
        "checkins": checkins,
        "boarding_passes": [ticket_service.boarding_pass(c["ticket_id"]) for c in checkins],
    }


def list_checkins(
    booking_id: str | None = None, pnr: str | None = None, flight_id: str | None = None, status: CheckinStatus | None = None
) -> list[dict]:
    def matches(c: dict) -> bool:
        return (
            (not booking_id or c["booking_id"] == booking_id)
            and (not pnr or c["pnr"] == pnr.upper())
            and (not flight_id or c["flight_id"] == flight_id)
            and (not status or c["status"] == status)
        )

    return sorted(db.checkins.filter(matches), key=lambda c: c["checkin_id"])


def get_checkin(checkin_id: str, actor: Principal) -> dict:
    checkin = db.checkins.get(checkin_id)
    booking = db.bookings.get(checkin["booking_id"]) if checkin else None
    if not booking or not owns(actor, booking["user_id"]):
        raise NotFoundError(f"Check-in {checkin_id} not found.")
    return checkin


def update_checkin(checkin_id: str, data, actor: Principal) -> dict:
    """Change the seat of a checked-in passenger, or offload them (cancels the ticket)."""
    with transaction():
        checkin = get_checkin(checkin_id, actor)
        if checkin["status"] != CheckinStatus.CHECKED_IN:
            raise ConflictError(f"Check-in {checkin_id} is {checkin['status']} and cannot be updated.")
        if flight_service.has_departed(flight_service.get_flight(checkin["flight_id"])):
            raise BadRequestError("Check-in cannot be changed after departure.")

        changes: dict = {"updated_at": now_iso()}
        ticket_id = checkin.get("ticket_id")

        if data.status == CheckinStatus.NOT_CHECKED_IN:
            changes["status"] = CheckinStatus.NOT_CHECKED_IN.value
            ticket = db.tickets.get(ticket_id) if ticket_id else None
            if ticket and ticket["status"] == TicketStatus.ISSUED:
                ticket_service.cancel_ticket(ticket_id)
        elif data.seat:
            if checkin["seat"] == INFANT_SEAT:
                raise BadRequestError("Infants do not have their own seat.")
            seat = data.seat.upper()
            if seat not in set(_seat_sequence(checkin["class_id"])):
                raise BadRequestError(f"Seat {seat} is not in the {checkin['class_id']} cabin.")
            if seat in _occupied_seats(checkin["flight_id"]) - {checkin["seat"]}:
                raise ConflictError(f"Seat {seat} is already taken.")
            changes["seat"] = seat
            if ticket_id:
                db.tickets.update(ticket_id, {"seat": seat})
        else:
            raise BadRequestError("Provide a new seat or status NOT_CHECKED_IN.")

        return db.checkins.update(checkin_id, changes)
