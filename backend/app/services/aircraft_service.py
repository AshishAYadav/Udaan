"""Aircraft lookup and rotation rule.

An aircraft is busy from departure until arrival plus the minimum ground
(turnaround) time: 4h after a domestic flight, 8h after an international one.
Two flights on the same aircraft conflict when their busy windows overlap.
"""
from datetime import datetime, timedelta

from app.config import settings
from app.db.database import repositories as db
from app.models.enums import FlightStatus
from app.services import reference_service as ref
from app.utils.errors import ConflictError, NotFoundError
from app.utils.timeutils import parse_dt


def list_aircraft() -> list[dict]:
    return sorted(db.aircrafts.all(), key=lambda a: a["aircraft_id"])


def get_aircraft(aircraft_id: str) -> dict:
    aircraft = db.aircrafts.get(aircraft_id)
    if not aircraft:
        raise NotFoundError(f"Aircraft {aircraft_id} not found.")
    return aircraft


def turnaround(domestic: bool) -> timedelta:
    return timedelta(hours=settings.turnaround_domestic_hours if domestic else settings.turnaround_international_hours)


def busy_window(departure: datetime, arrival: datetime, domestic: bool) -> tuple[datetime, datetime]:
    return departure, arrival + turnaround(domestic)


def find_conflict(
    aircraft_id: str, departure: datetime, arrival: datetime, domestic: bool, exclude_flight_id: str | None = None
) -> dict | None:
    """Return a flight on this aircraft whose busy window overlaps the proposed one."""
    airports = ref.airport_map()
    start, end = busy_window(departure, arrival, domestic)
    for flight in db.flights.find(aircraft_id=aircraft_id):
        if flight["flight_id"] == exclude_flight_id or flight["status"] == FlightStatus.CANCELLED:
            continue
        other_start, other_end = busy_window(
            parse_dt(flight["departure_time"]),
            parse_dt(flight["arrival_time"]),
            ref.is_domestic(flight["departure_airport"], flight["arrival_airport"], airports),
        )
        if start < other_end and other_start < end:
            return flight
    return None


def ensure_available(
    aircraft_id: str, departure: datetime, arrival: datetime, domestic: bool, exclude_flight_id: str | None = None
) -> None:
    conflict = find_conflict(aircraft_id, departure, arrival, domestic, exclude_flight_id)
    if conflict:
        raise ConflictError(
            f"Aircraft {aircraft_id} is operating flight {conflict['flight_number']} ({conflict['flight_id']}, "
            f"{conflict['departure_airport']}-{conflict['arrival_airport']} departing {conflict['departure_time']}). "
            f"An aircraft needs {settings.turnaround_domestic_hours}h ground time after a domestic flight and "
            f"{settings.turnaround_international_hours}h after an international flight."
        )


def available_aircraft(departure: datetime, arrival: datetime, domestic: bool) -> list[dict]:
    return [a for a in list_aircraft() if not find_conflict(a["aircraft_id"], departure, arrival, domestic)]
