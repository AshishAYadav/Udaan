"""Automatic flight schedule generation.

For every active route and every day in the range, the generator creates 3–4 flights spread over
the morning, afternoon and night banks, at random quarter-hour times. Each flight is validated
before it is stored:

- the route is active and both airports exist;
- the departure is in the future;
- the flight number (UD<slot><route no>, e.g. UD107) does not already operate that day;
- a suitable aircraft is free for the whole busy window: departure → arrival + ground time
  (4 h domestic / 8 h international), the same rule as manual scheduling. Wide-body aircraft
  fly long-haul routes (≥ 3,000 km) and narrow-body aircraft fly the rest.

A slot that cannot be filled is skipped and reported, never forced. Results are reproducible
for a given `seed`.
"""
import random
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import FlightStatus
from app.services import aircraft_service, fare_service
from app.services import reference_service as ref
from app.services.flight_service import compose_flight
from app.utils.errors import BadRequestError
from app.utils.timeutils import parse_dt, utcnow

BANKS = {  # local departure window in minutes after midnight
    "MORNING": (6 * 60, 11 * 60 + 45),
    "AFTERNOON": (12 * 60, 17 * 60 + 45),
    "NIGHT": (18 * 60, 23 * 60 + 30),
}
LONG_HAUL_KM = 3000
WIDE_BODY_MIN_SEATS = 250


def _is_wide_body(aircraft: dict) -> bool:
    return aircraft["total_seats"] >= WIDE_BODY_MIN_SEATS


def _busy_windows() -> dict[str, list[tuple[datetime, datetime]]]:
    airports = ref.airport_map()
    busy: dict[str, list[tuple[datetime, datetime]]] = {}
    for f in db.flights.scan(lambda f: f["status"] != FlightStatus.CANCELLED):
        domestic = ref.is_domestic(f["departure_airport"], f["arrival_airport"], airports)
        busy.setdefault(f["aircraft_id"], []).append(
            aircraft_service.busy_window(parse_dt(f["departure_time"]), parse_dt(f["arrival_time"]), domestic)
        )
    return busy


def _free(windows: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> bool:
    return all(not (start < other_end and other_start < end) for other_start, other_end in windows)


def _daily_times(rng: random.Random, count: int) -> list[int]:
    """One time in each bank, plus extra flights in random banks, at least 60 minutes apart."""
    banks = list(BANKS) + [rng.choice(list(BANKS)) for _ in range(max(0, count - len(BANKS)))]
    times: list[int] = []
    for bank in banks[:count]:
        low, high = BANKS[bank]
        for _ in range(10):
            minute = rng.randrange(low, high + 1, 15)
            if all(abs(minute - t) >= 60 for t in times):
                times.append(minute)
                break
    return sorted(times)


def generate(
    start: date,
    days: int,
    min_per_route: int = 3,
    max_per_route: int = 4,
    seed: int | None = None,
    route_ids: list[str] | None = None,
    new_id: Callable[[str], str] = next_id,
) -> dict:
    if not 1 <= days <= 120:
        raise BadRequestError("days must be between 1 and 120.")
    if not 1 <= min_per_route <= max_per_route <= 6:
        raise BadRequestError("Require 1 <= min_per_route <= max_per_route <= 6.")

    rng = random.Random(seed)
    airports = ref.airport_map()
    routes = [r for r in ref.list_routes(active=True) if not route_ids or r["route_id"] in route_ids]
    routes = [r for r in routes if r["origin"] in airports and r["destination"] in airports]
    if not routes:
        raise BadRequestError("No active routes to schedule.")
    fleet = aircraft_service.list_aircraft()
    wide = [a for a in fleet if _is_wide_body(a)]
    narrow = [a for a in fleet if not _is_wide_body(a)]

    busy = _busy_windows()
    taken_numbers = {(f["flight_number"], f["departure_date"]) for f in db.flights.scan(lambda f: True)}
    now = utcnow()
    flights, fares = [], []
    skipped: Counter[str] = Counter()

    with transaction():
        for offset in range(days):
            day = start + timedelta(days=offset)
            for route in routes:
                origin, destination = airports[route["origin"]], airports[route["destination"]]
                domestic = origin["country"] == destination["country"]
                preferred = wide if route["distance_km"] >= LONG_HAUL_KM else narrow
                pool = preferred or fleet
                count = rng.randint(min_per_route, max_per_route)
                for slot, minute in enumerate(_daily_times(rng, count), start=1):
                    departure = datetime.combine(day, time(minute // 60, minute % 60), ZoneInfo(origin["timezone"]))
                    if departure <= now:
                        skipped["departure in the past"] += 1
                        continue
                    number = f"UD{slot}{int(route['route_id'][2:]):02d}"
                    if (number, departure.date().isoformat()) in taken_numbers:
                        skipped["flight number already operating that day"] += 1
                        continue
                    arrival = departure + timedelta(minutes=route["duration_minutes"])
                    window = aircraft_service.busy_window(departure, arrival, domestic)
                    candidates = rng.sample(pool, len(pool))
                    plane = next((a for a in candidates if _free(busy.get(a["aircraft_id"], []), *window)), None)
                    if not plane:
                        skipped["no aircraft available"] += 1
                        continue
                    flight = compose_flight(new_id, number, route, plane["aircraft_id"], departure, destination["timezone"])
                    busy.setdefault(plane["aircraft_id"], []).append(window)
                    taken_numbers.add((number, flight["departure_date"]))
                    flights.append(flight)
                    fares.extend(fare_service.compose_fares(new_id, flight, plane, departure))
        if flights:
            db.flights.insert_many(flights)
            db.fares.insert_many(fares)

    return {
        "start_date": start,
        "end_date": start + timedelta(days=days - 1),
        "routes": len(routes),
        "created": len(flights),
        "skipped": sum(skipped.values()),
        "skipped_reasons": dict(skipped),
        "average_flights_per_day": round(len(flights) / days, 1),
    }
