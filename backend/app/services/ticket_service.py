"""Ticket issuance (only after check-in) and boarding passes."""
from datetime import timedelta
from html import escape

from app.auth.dependencies import Principal, owns
from app.config import settings
from app.db.database import next_id
from app.db.database import repositories as db
from app.models.enums import CheckinStatus, TicketStatus
from app.services import passenger_service
from app.services import reference_service as ref
from app.utils.errors import ConflictError, NotFoundError
from app.utils.ids import generate_ticket_number
from app.utils.timeutils import now_iso, parse_dt


def get_ticket(ticket_id: str) -> dict:
    ticket = db.tickets.get(ticket_id)
    if not ticket:
        raise NotFoundError(f"Ticket {ticket_id} not found.")
    return ticket


def get_accessible_ticket(ticket_id: str, actor: Principal | None, last_name: str | None = None) -> dict:
    """Booking owner and admins, or anyone with a matching passenger last name (PNR convention)."""
    ticket = db.tickets.get(ticket_id)
    booking = db.bookings.get(ticket["booking_id"]) if ticket else None
    if not booking or not (owns(actor, booking["user_id"]) or passenger_service.has_last_name(booking["passenger_ids"], last_name)):
        raise NotFoundError(f"Ticket {ticket_id} not found.")
    return ticket


def list_tickets(booking_id: str | None = None, pnr: str | None = None, status: TicketStatus | None = None) -> list[dict]:
    def matches(t: dict) -> bool:
        return (
            (not booking_id or t["booking_id"] == booking_id)
            and (not pnr or t["pnr"] == pnr.upper())
            and (not status or t["status"] == status)
        )

    return sorted(db.tickets.filter(matches), key=lambda t: t["ticket_id"])


def issue_ticket(checkin_id: str) -> dict:
    """Issue a ticket for a completed check-in. Rejects anything not checked in."""
    checkin = db.checkins.get(checkin_id)
    if not checkin:
        raise NotFoundError(f"Check-in {checkin_id} not found.")
    if checkin["status"] != CheckinStatus.CHECKED_IN:
        raise ConflictError("A ticket can only be issued after the passenger has checked in.")
    if db.tickets.find_one(checkin_id=checkin_id, status=TicketStatus.ISSUED.value):
        raise ConflictError(f"A ticket has already been issued for check-in {checkin_id}.")

    ticket = {
        "ticket_id": next_id("TKT"),
        "ticket_number": generate_ticket_number(),
        "checkin_id": checkin_id,
        "booking_id": checkin["booking_id"],
        "pnr": checkin["pnr"],
        "passenger_id": checkin["passenger_id"],
        "flight_id": checkin["flight_id"],
        "class_id": checkin["class_id"],
        "seat": checkin["seat"],
        "status": TicketStatus.ISSUED.value,
        "issued_at": now_iso(),
        "cancelled_at": None,
    }
    db.tickets.insert(ticket)
    db.checkins.update(checkin_id, {"ticket_id": ticket["ticket_id"]})
    return ticket


def cancel_ticket(ticket_id: str) -> dict:
    ticket = get_ticket(ticket_id)
    if ticket["status"] != TicketStatus.ISSUED:
        raise ConflictError(f"Ticket {ticket_id} is already {ticket['status']}.")
    return db.tickets.update(ticket_id, {"status": TicketStatus.CANCELLED.value, "cancelled_at": now_iso()})


def cancel_tickets_for_booking(booking_id: str) -> None:
    for ticket in db.tickets.find(booking_id=booking_id, status=TicketStatus.ISSUED.value):
        cancel_ticket(ticket["ticket_id"])


def boarding_pass(ticket_id: str) -> dict:
    """Boarding pass data for a ticket. Callers must check access first."""
    ticket = get_ticket(ticket_id)
    passenger = db.passengers.get(ticket["passenger_id"]) or {}
    flight = db.flights.get(ticket["flight_id"])
    checkin = db.checkins.get(ticket["checkin_id"]) or {}
    airports = ref.airport_map()
    departure = parse_dt(flight["departure_time"])
    boarding = departure - timedelta(minutes=settings.boarding_minutes_before_departure)
    return {
        "ticket_id": ticket["ticket_id"],
        "ticket_number": ticket["ticket_number"],
        "status": ticket["status"],
        "airline": settings.airline_name,
        "pnr": ticket["pnr"],
        "passenger_name": f"{passenger.get('last_name', '').upper()}/{passenger.get('first_name', '').upper()}",
        "passenger_type": passenger.get("passenger_type", "ADULT"),
        "flight_number": flight["flight_number"],
        "origin": ref.airport_brief(airports[flight["departure_airport"]]),
        "destination": ref.airport_brief(airports[flight["arrival_airport"]]),
        "departure_time": flight["departure_time"],
        "arrival_time": flight["arrival_time"],
        "departure_date": departure.strftime("%d %b %Y"),
        "departure_local_time": departure.strftime("%H:%M"),
        "boarding_time": boarding.strftime("%H:%M"),
        "gate": "TBA",
        "cabin": ticket["class_id"],
        "cabin_name": ref.class_names().get(ticket["class_id"], ticket["class_id"]),
        "seat": ticket["seat"],
        "sequence_number": checkin.get("sequence_number", 0),
    }


def boarding_pass_html(ticket_id: str) -> str:
    bp = boarding_pass(ticket_id)
    rows = [
        ("Passenger", bp["passenger_name"]),
        ("PNR", bp["pnr"]),
        ("Ticket", bp["ticket_number"]),
        ("Flight", bp["flight_number"]),
        ("From", f"{bp['origin']['code']} - {bp['origin']['city']}"),
        ("To", f"{bp['destination']['code']} - {bp['destination']['city']}"),
        ("Date", bp["departure_date"]),
        ("Departure", bp["departure_local_time"]),
        ("Boarding", bp["boarding_time"]),
        ("Cabin", bp["cabin_name"]),
        ("Seat", bp["seat"]),
        ("Gate", bp["gate"]),
        ("Status", bp["status"]),
    ]
    cells = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Boarding pass {escape(bp['ticket_number'])}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#111}}
.pass{{max-width:560px;border:2px dashed #555;border-radius:12px;padding:1.5rem}}
h1{{margin:0 0 1rem;font-size:1.3rem}} th{{text-align:left;padding:.25rem 1rem .25rem 0;color:#555}}
@media print{{button{{display:none}}}}
</style></head>
<body><div class="pass"><h1>{escape(bp['airline'])} &mdash; Boarding Pass</h1><table>{cells}</table></div>
<p><button onclick="window.print()">Print</button></p></body></html>"""
