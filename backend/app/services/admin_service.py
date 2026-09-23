"""Aggregates for the admin dashboard."""
from app.db.database import repositories as db
from app.models.enums import ACTIVE_BOOKING_STATUSES, TicketStatus
from app.services import flight_service


def summary() -> dict:
    return {
        "airports": db.airports.count(),
        "routes": db.routes.count(),
        "aircraft": db.aircrafts.count(),
        "flights_total": db.flights.count(),
        "flights_upcoming": len(flight_service.list_flights(upcoming_only=True)),
        "users": db.users.count(),
        "passengers": db.passengers.count(),
        "bookings_total": db.bookings.count(),
        "bookings_active": len(db.bookings.filter(lambda b: b["status"] in ACTIVE_BOOKING_STATUSES)),
        "checkins": db.checkins.count(),
        "tickets_issued": len(db.tickets.find(status=TicketStatus.ISSUED.value)),
    }
