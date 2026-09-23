"""Flight search and flight schedule management."""
from collections.abc import Callable
from datetime import date, datetime, timedelta

from app.config import settings
from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import BOOKABLE_FLIGHT_STATUSES, FlightPhase, FlightStatus
from app.services import aircraft_service, baggage_service, fare_service
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ConflictError, NotFoundError
from app.utils.timeutils import in_timezone, now_iso, parse_dt, utcnow


def compose_flight(
    new_id: Callable[[str], str],
    flight_number: str,
    route: dict,
    aircraft_id: str,
    departure: datetime,
    arrival_tz: str,
) -> dict:
    """Build a flight record. ``departure`` must be aware and in the origin timezone."""
    arrival = in_timezone(departure + timedelta(minutes=route["duration_minutes"]), arrival_tz)
    return {
        "flight_id": new_id("FLT"),
        "flight_number": flight_number,
        "route_id": route["route_id"],
        "aircraft_id": aircraft_id,
        "departure_airport": route["origin"],
        "arrival_airport": route["destination"],
        "departure_time": departure.isoformat(),
        "arrival_time": arrival.isoformat(),
        "departure_date": departure.date().isoformat(),
        "duration_minutes": route["duration_minutes"],
        "status": FlightStatus.SCHEDULED.value,
        "created_at": now_iso(),
        "updated_at": None,
    }


def get_flight(flight_id: str) -> dict:
    flight = db.flights.get(flight_id)
    if not flight:
        raise NotFoundError(f"Flight {flight_id} not found.")
    return flight


def has_departed(flight: dict) -> bool:
    return parse_dt(flight["departure_time"]) <= utcnow()


def phase(flight: dict, now: datetime | None = None) -> FlightPhase:
    """Operational phase from the departure timeline (check-in, boarding, gate, departure, arrival)."""
    if flight["status"] == FlightStatus.CANCELLED:
        return FlightPhase.CANCELLED
    now = now or utcnow()
    departure, arrival = parse_dt(flight["departure_time"]), parse_dt(flight["arrival_time"])
    if now >= arrival:
        return FlightPhase.ARRIVED
    if now >= departure or flight["status"] == FlightStatus.DEPARTED:
        return FlightPhase.DEPARTED
    minutes_left = (departure - now).total_seconds() / 60
    if minutes_left <= settings.boarding_closes_minutes:
        return FlightPhase.GATE_CLOSED
    if minutes_left <= settings.boarding_opens_minutes:
        return FlightPhase.BOARDING
    if minutes_left <= settings.checkin_closes_minutes:
        return FlightPhase.CHECKIN_CLOSED
    if minutes_left <= settings.checkin_opens_hours * 60:
        return FlightPhase.CHECKIN_OPEN
    return FlightPhase.SCHEDULED


def get_bookable_flight(flight_id: str) -> dict:
    flight = get_flight(flight_id)
    if flight["status"] not in BOOKABLE_FLIGHT_STATUSES:
        raise BadRequestError(f"Flight {flight['flight_number']} is {flight['status']} and cannot be booked.")
    if has_departed(flight):
        raise BadRequestError(f"Flight {flight['flight_number']} has already departed.")
    return flight


def summarize(flight: dict, airports: dict | None = None, aircraft: dict | None = None) -> dict:
    airports = airports or ref.airport_map()
    aircraft = aircraft or db.aircrafts.get(flight["aircraft_id"]) or {}
    return {
        "flight_id": flight["flight_id"],
        "flight_number": flight["flight_number"],
        "origin": ref.airport_brief(airports[flight["departure_airport"]]),
        "destination": ref.airport_brief(airports[flight["arrival_airport"]]),
        "departure": flight["departure_time"],
        "arrival": flight["arrival_time"],
        "duration_minutes": flight["duration_minutes"],
        "status": flight["status"],
        "phase": phase(flight),
        "domestic": ref.is_domestic(flight["departure_airport"], flight["arrival_airport"], airports),
        "aircraft_model": aircraft.get("model", "Unknown"),
    }


def search_flights(
    origin: str, destination: str, travel_date: date, class_id: str | None = None, passengers: int = 1
) -> list[dict]:
    """Bookable flights on a route for a local departure date with enough seats."""
    origin, destination = origin.upper(), destination.upper()
    ref.get_airport(origin)
    ref.get_airport(destination)
    if origin == destination:
        raise BadRequestError("Origin and destination must be different.")

    airports = ref.airport_map()
    aircraft = {a["aircraft_id"]: a for a in db.aircrafts.all()}
    names = ref.class_names()
    day = travel_date.isoformat()

    results = []
    candidates = db.flights.filter(
        lambda f: f["departure_airport"] == origin
        and f["arrival_airport"] == destination
        and f["departure_date"] == day
        and f["status"] in BOOKABLE_FLIGHT_STATUSES
    )
    fares = fare_service.fares_by_flight({f["flight_id"] for f in candidates})
    for flight in candidates:
        if has_departed(flight):
            continue
        classes = [
            {
                "class_id": fare["class_id"],
                "name": names.get(fare["class_id"], fare["class_id"]),
                "fare_id": fare["fare_id"],
                "price": fare["base_price"],
                "currency": fare["currency"],
                "available_seats": fare["available_seats"],
                "baggage": baggage_service.for_party(
                    ref.is_domestic(origin, destination, airports), fare["class_id"]
                ),
            }
            for fare in sorted(fares.get(flight["flight_id"], []), key=lambda f: f["base_price"])
            if fare["available_seats"] >= passengers and (class_id is None or fare["class_id"] == class_id)
        ]
        if not classes:
            continue
        results.append(
            {
                **summarize(flight, airports, aircraft.get(flight["aircraft_id"])),
                "available_classes": classes,
                "starting_fare": classes[0]["price"],
                "currency": classes[0]["currency"],
                "available_seats": sum(c["available_seats"] for c in classes),
            }
        )
    return sorted(results, key=lambda r: parse_dt(r["departure"]))


def list_flights(
    origin: str | None = None,
    destination: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: FlightStatus | None = None,
    aircraft_id: str | None = None,
    upcoming_only: bool = False,
) -> list[dict]:
    def matches(f: dict) -> bool:
        return (
            (not origin or f["departure_airport"] == origin.upper())
            and (not destination or f["arrival_airport"] == destination.upper())
            and (not date_from or f["departure_date"] >= date_from.isoformat())
            and (not date_to or f["departure_date"] <= date_to.isoformat())
            and (not status or f["status"] == status)
            and (not aircraft_id or f["aircraft_id"] == aircraft_id)
        )

    flights = db.flights.filter(matches)
    if upcoming_only:
        flights = [f for f in flights if not has_departed(f)]
    return sorted(flights, key=lambda f: parse_dt(f["departure_time"]))


def _schedule_view(flight: dict, aircraft: dict, fares: list[dict]) -> dict:
    capacity = sum(f["total_seats"] for f in fares)
    available = sum(f["available_seats"] for f in fares)
    return {
        **flight,
        "phase": phase(flight),
        "aircraft_registration": aircraft.get("registration", ""),
        "aircraft_model": aircraft.get("model", ""),
        "capacity": capacity,
        "seats_sold": capacity - available,
        "available_seats": available,
    }


def list_schedules(limit: int, offset: int, **filters) -> dict:
    flights = list_flights(**filters)
    aircraft = {a["aircraft_id"]: a for a in db.aircrafts.all()}
    page = flights[offset : offset + limit]
    fares = fare_service.fares_by_flight({f["flight_id"] for f in page})
    return {
        "total": len(flights),
        "limit": limit,
        "offset": offset,
        "items": [_schedule_view(f, aircraft.get(f["aircraft_id"], {}), fares.get(f["flight_id"], [])) for f in page],
    }


def get_schedule(flight_id: str) -> dict:
    flight = get_flight(flight_id)
    return _schedule_view(flight, db.aircrafts.get(flight["aircraft_id"]) or {}, db.fares.find(flight_id=flight_id))


def _ensure_unique_flight_number(flight_number: str, departure_date: str, exclude_flight_id: str | None = None):
    for other in db.flights.find(flight_number=flight_number, departure_date=departure_date):
        if other["flight_id"] != exclude_flight_id and other["status"] != FlightStatus.CANCELLED:
            raise ConflictError(f"Flight number {flight_number} already operates on {departure_date}.")


def create_schedule(data) -> dict:
    route = ref.get_route(data.route_id)
    if not route["active"]:
        raise BadRequestError(f"Route {route['route_id']} is not active.")
    aircraft = aircraft_service.get_aircraft(data.aircraft_id)
    origin = ref.get_airport(route["origin"])
    destination = ref.get_airport(route["destination"])

    departure = in_timezone(data.departure_time, origin["timezone"])
    if departure <= utcnow():
        raise BadRequestError("Departure time must be in the future.")
    unknown = set(data.fares or {}) - set(aircraft["cabin_configuration"])
    if unknown:
        raise BadRequestError(f"Aircraft {aircraft['aircraft_id']} has no cabin(s): {', '.join(sorted(unknown))}.")

    arrival = departure + timedelta(minutes=route["duration_minutes"])
    domestic = origin["country"] == destination["country"]

    with transaction():
        aircraft_service.ensure_available(aircraft["aircraft_id"], departure, arrival, domestic)
        _ensure_unique_flight_number(data.flight_number, departure.date().isoformat())
        flight = compose_flight(next_id, data.flight_number, route, aircraft["aircraft_id"], departure, destination["timezone"])
        db.flights.insert(flight)
        db.fares.insert_many(fare_service.compose_fares(next_id, flight, aircraft, departure, data.fares))
    return get_schedule(flight["flight_id"])


def _resize_fares(flight_id: str, aircraft: dict) -> None:
    """Re-map seat inventory onto a new aircraft, keeping seats already sold."""
    config = aircraft["cabin_configuration"]
    for fare in db.fares.find(flight_id=flight_id):
        sold = fare["total_seats"] - fare["available_seats"]
        capacity = config.get(fare["class_id"], 0)
        if capacity < sold:
            raise ConflictError(
                f"Aircraft {aircraft['aircraft_id']} has {capacity} {fare['class_id']} seats "
                f"but {sold} are already sold."
            )
        db.fares.update(fare["fare_id"], {"total_seats": capacity, "available_seats": capacity - sold})


def modify_schedule(flight_id: str, data) -> dict:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise BadRequestError("No changes supplied.")

    with transaction():
        flight = get_flight(flight_id)
        if flight["status"] in {FlightStatus.DEPARTED, FlightStatus.CANCELLED} and "status" not in changes:
            raise ConflictError(f"Flight {flight_id} is {flight['status']} and cannot be modified.")

        route = ref.get_route(flight["route_id"])
        origin = ref.get_airport(route["origin"])
        destination = ref.get_airport(route["destination"])
        departure = parse_dt(flight["departure_time"])
        aircraft_id = changes.get("aircraft_id", flight["aircraft_id"])
        flight_number = changes.get("flight_number", flight["flight_number"])
        update: dict = {}

        if "departure_time" in changes:
            departure = in_timezone(changes["departure_time"], origin["timezone"])
            if departure <= utcnow():
                raise BadRequestError("Departure time must be in the future.")
            arrival = in_timezone(departure + timedelta(minutes=route["duration_minutes"]), destination["timezone"])
            update |= {
                "departure_time": departure.isoformat(),
                "arrival_time": arrival.isoformat(),
                "departure_date": departure.date().isoformat(),
            }

        if "aircraft_id" in changes or "departure_time" in changes:
            aircraft = aircraft_service.get_aircraft(aircraft_id)
            aircraft_service.ensure_available(
                aircraft_id,
                departure,
                departure + timedelta(minutes=route["duration_minutes"]),
                origin["country"] == destination["country"],
                exclude_flight_id=flight_id,
            )
            if aircraft_id != flight["aircraft_id"]:
                _resize_fares(flight_id, aircraft)
                update["aircraft_id"] = aircraft_id

        if "flight_number" in changes or "departure_time" in changes:
            _ensure_unique_flight_number(flight_number, departure.date().isoformat(), exclude_flight_id=flight_id)
            update["flight_number"] = flight_number

        if "status" in changes:
            update["status"] = changes["status"].value

        update["updated_at"] = now_iso()
        db.flights.update(flight_id, update)
    return get_schedule(flight_id)
