"""Online check-in by PNR + last name.

Check-in is per journey (through check-in): checking in for the outbound journey
checks passengers in on every remaining segment of it and issues one ticket /
boarding pass per passenger per segment. The return journey is checked in
separately. Check-in opens `checkin_opens_hours` before departure (0 = at any
time) and closes `checkin_closes_minutes` before departure.
"""
from collections.abc import Iterator
from datetime import timedelta

from app.auth.dependencies import Principal, owns
from app.config import settings
from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import (
    ACTIVE_BOOKING_STATUSES,
    CabinClass,
    CheckinStatus,
    Direction,
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


def _window_error(flight: dict) -> str | None:
    departure = parse_dt(flight["departure_time"])
    now = utcnow()
    if settings.checkin_opens_hours and now < departure - timedelta(hours=settings.checkin_opens_hours):
        return f"Check-in for {flight['flight_number']} opens {settings.checkin_opens_hours} hours before departure."
    if now > departure - timedelta(minutes=settings.checkin_closes_minutes):
        return f"Check-in for {flight['flight_number']} closed {settings.checkin_closes_minutes} minutes before departure."
    return None


def _journey_plan(booking: dict, direction: Direction | None) -> dict:
    """Pick the journey to check in and work out which passengers are eligible."""
    if booking["status"] not in ACTIVE_BOOKING_STATUSES:
        return {"direction": direction, "flights": [], "eligible": [], "reasons": [f"Booking is {booking['status']}."]}

    directions = [direction] if direction else [Direction.OUTBOUND, Direction.RETURN]
    fallback = None  # first upcoming journey, reported when nothing is eligible
    for d in directions:
        flights = [flight_service.get_flight(fid) for fid in booking_service.journey_ids(booking, d)]
        remaining = [f for f in flights if not flight_service.has_departed(f) and f["status"] != FlightStatus.DEPARTED]
        if not flights or (not remaining and not direction):
            continue
        reasons: list[str] = []
        if not remaining:
            reasons.append("This journey has already departed.")
        elif any(f["status"] == FlightStatus.CANCELLED for f in remaining):
            reasons.append("A flight in this journey has been cancelled.")
        elif error := _window_error(remaining[0]):
            reasons.append(error)
        if not reasons:
            done = {fid: _checked_in(booking["booking_id"], fid) for fid in (f["flight_id"] for f in remaining)}
            eligible = [pid for pid in booking["passenger_ids"] if any(pid not in ids for ids in done.values())]
            if len(eligible) < len(booking["passenger_ids"]):
                reasons.append(f"{len(booking['passenger_ids']) - len(eligible)} passenger(s) already checked in for this journey.")
            if eligible:
                return {"direction": d, "flights": remaining, "eligible": eligible, "reasons": reasons}
        # Nothing to do on this journey: move on to the next one unless a direction was requested.
        fallback = fallback or {"direction": d, "flights": remaining, "eligible": [], "reasons": reasons}
    return fallback or {"direction": direction, "flights": [], "eligible": [], "reasons": ["No upcoming journey to check in."]}


def validate(pnr: str, last_name: str, direction: Direction | None = None) -> dict:
    booking = booking_service.find_by_pnr(pnr, last_name)
    plan = _journey_plan(booking, direction)
    return {
        "booking": booking_service.build_view(booking),
        "direction": plan["direction"],
        "flight_ids": [f["flight_id"] for f in plan["flights"]],
        "can_check_in": bool(plan["eligible"]),
        "eligible_passenger_ids": plan["eligible"],
        "reasons": plan["reasons"],
    }


def check_in(data) -> dict:
    """Check passengers in on every remaining segment of a journey and issue boarding passes."""
    booking = booking_service.find_by_pnr(data.pnr, data.last_name)
    with transaction():
        plan = _journey_plan(booking, data.direction)
        requested = data.passenger_ids or plan["eligible"]
        if not requested:
            raise ConflictError(" ".join(plan["reasons"]) or "No passengers are eligible for check-in.")
        for pid in requested:
            if pid not in booking["passenger_ids"]:
                raise BadRequestError(f"Passenger {pid} is not on booking {booking['pnr']}.")
            if pid not in plan["eligible"]:
                raise ConflictError(f"Passenger {pid} is already checked in or not eligible. {' '.join(plan['reasons'])}".strip())

        passengers = {pid: db.passengers.get(pid) for pid in requested}
        seated = [pid for pid in requested if passengers[pid]["passenger_type"] != PassengerType.INFANT]
        infants = [pid for pid in requested if pid not in seated]

        checkins = []
        for flight in plan["flights"]:
            already = _checked_in(booking["booking_id"], flight["flight_id"])
            if infants and not seated and not already:
                raise BadRequestError("Infants must be checked in together with, or after, an accompanying adult.")
            taken = _occupied_seats(flight["flight_id"])
            sequence = len(db.checkins.find(flight_id=flight["flight_id"]))
            for pid in seated + infants:
                if pid in already:
                    continue
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
                    "flight_id": flight["flight_id"],
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

    return {
        "booking_id": booking["booking_id"],
        "pnr": booking["pnr"],
        "direction": plan["direction"],
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
