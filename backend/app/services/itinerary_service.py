"""Journeys (one or more connecting segments) and trips (outbound + optional return).

Connection rules (industry convention, configurable in config.py):
- the next segment departs from the airport the previous one arrived at;
- layover >= minimum connecting time (60 min domestic, 90 min international);
- layover <= maximum connection time (4h domestic, 24h international); beyond
  that it is a stopover, not a connection;
- a journey never revisits an airport.
"""
from datetime import date, timedelta

from app.config import settings
from app.db.database import repositories as db
from app.models.enums import BOOKABLE_FLIGHT_STATUSES, HOLDING_BOOKING_STATUSES, PassengerType, TripType
from app.services import baggage_service, fare_service, flight_service, passenger_service
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ForbiddenError
from app.utils.timeutils import parse_dt, utcnow

MAX_STOPS = 1


def connection_limits(domestic: bool) -> tuple[timedelta, timedelta]:
    if domestic:
        return (
            timedelta(minutes=settings.min_connection_domestic_minutes),
            timedelta(hours=settings.max_connection_domestic_hours),
        )
    return (
        timedelta(minutes=settings.min_connection_international_minutes),
        timedelta(hours=settings.max_connection_international_hours),
    )


def _is_domestic_connection(first: dict, second: dict, airports: dict) -> bool:
    return ref.is_domestic(first["departure_airport"], first["arrival_airport"], airports) and ref.is_domestic(
        second["departure_airport"], second["arrival_airport"], airports
    )


def connection_error(first: dict, second: dict, airports: dict | None = None) -> str | None:
    """Why `second` cannot follow `first` in a journey, or None if it can."""
    airports = airports or ref.airport_map()
    hub = first["arrival_airport"]
    if second["departure_airport"] != hub:
        return f"Flight {second['flight_number']} does not depart from {hub}, where {first['flight_number']} arrives."
    layover = parse_dt(second["departure_time"]) - parse_dt(first["arrival_time"])
    minimum, maximum = connection_limits(_is_domestic_connection(first, second, airports))
    if layover < minimum:
        return f"Connection at {hub} is {_minutes(layover)} min; the minimum connecting time is {_minutes(minimum)} min."
    if layover > maximum:
        return f"Connection at {hub} is {_minutes(layover)} min; the maximum is {_minutes(maximum)} min (longer is a stopover)."
    return None


def _minutes(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


def load_journey(flight_ids: list[str]) -> list[dict]:
    """Load bookable flights for a journey and validate its connections."""
    if not flight_ids:
        raise BadRequestError("A journey needs at least one flight.")
    if len(flight_ids) > MAX_STOPS + 1:
        raise BadRequestError(f"A journey can have at most {MAX_STOPS} connection(s).")
    flights = [flight_service.get_bookable_flight(fid) for fid in flight_ids]
    airports = ref.airport_map()
    for first, second in zip(flights, flights[1:]):
        error = connection_error(first, second, airports)
        if error:
            raise BadRequestError(error)
    visited = [flights[0]["departure_airport"], *(f["arrival_airport"] for f in flights)]
    if len(set(visited)) != len(visited):
        raise BadRequestError("A journey cannot visit the same airport twice.")
    return flights


def validate_trip(outbound: list[dict], inbound: list[dict]) -> None:
    """A return journey must reverse the outbound journey and depart after it arrives."""
    if not inbound:
        return
    origin, destination = outbound[0]["departure_airport"], outbound[-1]["arrival_airport"]
    if inbound[0]["departure_airport"] != destination or inbound[-1]["arrival_airport"] != origin:
        raise BadRequestError(f"The return journey must fly {destination} → {origin}.")
    minimum, _ = connection_limits(ref.is_domestic(origin, destination))
    if parse_dt(inbound[0]["departure_time"]) < parse_dt(outbound[-1]["arrival_time"]) + minimum:
        raise BadRequestError("The return journey must depart after the outbound journey arrives.")


def prepare_trip(outbound_ids: list[str], return_ids: list[str], class_id: str, passenger_ids: list[str]) -> dict:
    """Validate a trip for a cabin and party, and price it. Used by payments and bookings."""
    outbound = load_journey(outbound_ids)
    inbound = load_journey(return_ids) if return_ids else []
    validate_trip(outbound, inbound)
    flights = outbound + inbound
    if len({f["flight_id"] for f in flights}) != len(flights):
        raise BadRequestError("The same flight cannot appear twice in a trip.")

    party = passenger_service.validate_party(passenger_ids, date.fromisoformat(outbound[0]["departure_date"]))
    seats = fare_service.seats_required(party)
    fares = [fare_service.get_fare(f["flight_id"], class_id) for f in flights]
    for fare in fares:
        fare_service.ensure_seats(fare, seats)
    return {
        "outbound": outbound,
        "inbound": inbound,
        "flights": flights,
        "fares": fares,
        "party": party,
        "seats": seats,
        "quote": fare_service.quote(fares, party),
        "trip_type": TripType.ROUND_TRIP if inbound else TripType.ONE_WAY,
    }


def ensure_passengers_belong_to(party: list[dict], user_id: str | None) -> None:
    """Passengers must be owned by the booking user, or be unowned (guest) and not on another live booking.

    The second rule stops anyone reusing another guest's passenger records.
    """
    booked = {pid for b in db.bookings.scan(lambda b: b["status"] in HOLDING_BOOKING_STATUSES) for pid in b["passenger_ids"]}
    foreign = [
        p["passenger_id"]
        for p in party
        if not ((p.get("user_id") and p["user_id"] == user_id) or (not p.get("user_id") and p["passenger_id"] not in booked))
    ]
    if foreign:
        raise ForbiddenError(f"Passenger(s) {', '.join(foreign)} cannot be used on this booking.")


# Search

def _bookable_after_now(flight: dict) -> bool:
    return flight["status"] in BOOKABLE_FLIGHT_STATUSES and not flight_service.has_departed(flight)


def _type_price(fares: list[dict], passenger_type: PassengerType) -> float:
    """Price per passenger of a type over all segments, rounded per segment like payment quotes."""
    factor = fare_service.PASSENGER_FARE_FACTOR[passenger_type]
    return round(sum(round(f["base_price"] * factor, 2) for f in fares), 2)


def _itinerary(flights: list[dict], fares_by_flight: dict, names: dict, airports: dict, aircraft: dict,
               class_id: str | None, party: dict[PassengerType, int]) -> dict | None:
    """Build an itinerary offering the cabins available on every segment, or None."""
    per_flight = [{f["class_id"]: f for f in fares_by_flight.get(fl["flight_id"], [])} for fl in flights]
    common = set.intersection(*(set(p) for p in per_flight))
    seats = party[PassengerType.ADULT] + party[PassengerType.CHILD]
    domestic = all(ref.is_domestic(f["departure_airport"], f["arrival_airport"], airports) for f in flights)
    classes = []
    for cid in common:
        segment_fares = [p[cid] for p in per_flight]
        if (class_id and cid != class_id) or min(f["available_seats"] for f in segment_fares) < seats:
            continue
        prices = {t: _type_price(segment_fares, t) for t in PassengerType}
        classes.append(
            {
                "class_id": cid,
                "name": names.get(cid, cid),
                "price": prices[PassengerType.ADULT],
                "child_price": prices[PassengerType.CHILD],
                "infant_price": prices[PassengerType.INFANT],
                "party_total": round(sum(prices[t] * n for t, n in party.items()), 2),
                "currency": segment_fares[0]["currency"],
                "available_seats": min(f["available_seats"] for f in segment_fares),
                "baggage": baggage_service.for_party(domestic, cid),
            }
        )
    if not classes:
        return None
    classes.sort(key=lambda c: c["price"])
    departure, arrival = parse_dt(flights[0]["departure_time"]), parse_dt(flights[-1]["arrival_time"])
    return {
        "itinerary_id": "-".join(f["flight_id"] for f in flights),
        "flight_ids": [f["flight_id"] for f in flights],
        "stops": len(flights) - 1,
        "domestic": domestic,
        "origin": ref.airport_brief(airports[flights[0]["departure_airport"]]),
        "destination": ref.airport_brief(airports[flights[-1]["arrival_airport"]]),
        "departure": flights[0]["departure_time"],
        "arrival": flights[-1]["arrival_time"],
        "total_duration_minutes": _minutes(arrival - departure),
        "segments": [flight_service.summarize(f, airports, aircraft.get(f["aircraft_id"])) for f in flights],
        "layovers": [
            {
                "airport": ref.airport_brief(airports[a["arrival_airport"]]),
                "minutes": _minutes(parse_dt(b["departure_time"]) - parse_dt(a["arrival_time"])),
            }
            for a, b in zip(flights, flights[1:])
        ],
        "available_classes": classes,
        "starting_fare": classes[0]["price"],
        "currency": classes[0]["currency"],
    }


def search_itineraries(
    origin: str, destination: str, travel_date: date, class_id: str | None, party: dict[PassengerType, int]
) -> list[dict]:
    """Direct and one-stop itineraries whose first flight departs on the local travel date."""
    origin, destination = origin.upper(), destination.upper()
    ref.get_airport(origin)
    ref.get_airport(destination)
    if origin == destination:
        raise BadRequestError("Origin and destination must be different.")

    airports = ref.airport_map()
    aircraft = {a["aircraft_id"]: a for a in db.aircrafts.all()}
    names = ref.class_names()
    day = travel_date.isoformat()
    _, longest = connection_limits(domestic=False)
    # Second legs may depart up to the maximum connection time after the first leg lands.
    last_day = (travel_date + timedelta(days=longest.days + 2)).isoformat()

    candidates = [
        f for f in db.flights.scan(lambda f: day <= f["departure_date"] <= last_day) if _bookable_after_now(f)
    ]
    fares = fare_service.fares_by_flight({f["flight_id"] for f in candidates})
    first_legs = [f for f in candidates if f["departure_airport"] == origin and f["departure_date"] == day]
    arriving = [f for f in candidates if f["arrival_airport"] == destination]

    journeys = [[f] for f in first_legs if f["arrival_airport"] == destination]
    for first in first_legs:
        if first["arrival_airport"] == destination:
            continue
        for second in arriving:
            if second["departure_airport"] == first["arrival_airport"] and not connection_error(first, second, airports):
                journeys.append([first, second])

    itineraries = [
        it for it in (_itinerary(j, fares, names, airports, aircraft, class_id, party) for j in journeys) if it
    ]
    return sorted(itineraries, key=lambda i: (i["stops"], parse_dt(i["departure"]), i["total_duration_minutes"]))


def search_trip(
    origin: str, destination: str, departure_date: date, return_date: date | None,
    class_id: str | None = None, adults: int = 1, children: int = 0, infants: int = 0,
) -> dict:
    if adults < 1:
        raise BadRequestError("At least one adult is required; children and infants must travel with an adult.")
    if infants > adults:
        raise BadRequestError("Each infant must travel on the lap of a separate adult.")
    if adults + children > settings.max_seats_per_booking:
        raise BadRequestError(f"At most {settings.max_seats_per_booking} seated passengers per booking.")
    party = {PassengerType.ADULT: adults, PassengerType.CHILD: children, PassengerType.INFANT: infants}
    if return_date and return_date < departure_date:
        raise BadRequestError("Return date cannot be before the departure date.")
    if departure_date < utcnow().date() - timedelta(days=1):
        raise BadRequestError("Departure date is in the past.")
    return {
        "trip_type": TripType.ROUND_TRIP if return_date else TripType.ONE_WAY,
        "party": {"adults": adults, "children": children, "infants": infants},
        "outbound": search_itineraries(origin, destination, departure_date, class_id, party),
        "return": search_itineraries(destination, origin, return_date, class_id, party) if return_date else [],
    }
