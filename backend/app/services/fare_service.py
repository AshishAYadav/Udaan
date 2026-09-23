"""Fares, passenger pricing, seat inventory and SSR pricing."""
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from app.config import settings
from app.db.database import repositories as db
from app.db.database import transaction
from app.models.enums import CabinClass, PassengerType
from app.utils.errors import BadRequestError, ConflictError, NotFoundError

CABIN_PRICE_FACTOR = {
    CabinClass.ECONOMY: 1.0,
    CabinClass.PREMIUM_ECONOMY: 1.6,
    CabinClass.BUSINESS: 3.2,
    CabinClass.FIRST: 5.5,
}

PASSENGER_FARE_FACTOR = {
    PassengerType.ADULT: 1.0,
    PassengerType.CHILD: settings.child_fare_factor,
    PassengerType.INFANT: settings.infant_fare_factor,
}


def default_base_price(duration_minutes: int, class_id: str, departure: datetime) -> float:
    """Deterministic prototype pricing: distance-based with a weekend surcharge."""
    economy = 80 + duration_minutes * 0.8
    if departure.weekday() >= 5:
        economy *= 1.1
    return round(economy * CABIN_PRICE_FACTOR[CabinClass(class_id)], 2)


def compose_fares(
    new_id: Callable[[str], str],
    flight: dict,
    aircraft: dict,
    departure: datetime,
    overrides: dict[str, float] | None = None,
) -> list[dict]:
    """Build one fare record per cabin configured on the aircraft."""
    overrides = overrides or {}
    fares = []
    for class_id, seats in aircraft["cabin_configuration"].items():
        if seats <= 0:
            continue
        price = overrides.get(class_id) or default_base_price(flight["duration_minutes"], class_id, departure)
        fares.append(
            {
                "fare_id": new_id("FARE"),
                "flight_id": flight["flight_id"],
                "class_id": class_id,
                "fare_type": "STANDARD",
                "base_price": float(price),
                "currency": settings.currency,
                "total_seats": seats,
                "available_seats": seats,
            }
        )
    return fares


def fares_for_flight(flight_id: str) -> list[dict]:
    if not db.flights.get(flight_id):
        raise NotFoundError(f"Flight {flight_id} not found.")
    fares = sorted(db.fares.find(flight_id=flight_id), key=lambda f: f["base_price"])
    return [
        {
            **f,
            "child_price": round(f["base_price"] * PASSENGER_FARE_FACTOR[PassengerType.CHILD], 2),
            "infant_price": round(f["base_price"] * PASSENGER_FARE_FACTOR[PassengerType.INFANT], 2),
        }
        for f in fares
    ]


def fares_by_flight(flight_ids: set[str]) -> dict[str, list[dict]]:
    """Read-only fares grouped by flight, for the given flights."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for fare in db.fares.scan(lambda f: f["flight_id"] in flight_ids):
        grouped[fare["flight_id"]].append(fare)
    return grouped


def get_fare(flight_id: str, class_id: str) -> dict:
    fare = db.fares.find_one(flight_id=flight_id, class_id=class_id)
    if not fare:
        raise BadRequestError(f"Cabin class {class_id} is not offered on flight {flight_id}.")
    return fare


def seats_required(passengers: list[dict]) -> int:
    """Infants travel on an adult's lap and do not occupy a seat."""
    return sum(1 for p in passengers if p["passenger_type"] != PassengerType.INFANT)


def quote(fares: list[dict], passengers: list[dict]) -> dict:
    """Price a party over one fare per segment. Passengers carry their effective passenger_type."""
    lines = [
        {
            "passenger_id": p["passenger_id"],
            "passenger_type": p["passenger_type"],
            "flight_id": fare["flight_id"],
            "amount": round(fare["base_price"] * PASSENGER_FARE_FACTOR[PassengerType(p["passenger_type"])], 2),
        }
        for fare in fares
        for p in passengers
    ]
    return {"lines": lines, "total": round(sum(line["amount"] for line in lines), 2), "currency": fares[0]["currency"]}


def ensure_seats(fare: dict, count: int) -> None:
    if fare["available_seats"] < count:
        raise ConflictError(
            f"Not enough seats in {fare['class_id']} on flight {fare['flight_id']}: "
            f"requested {count}, available {fare['available_seats']}."
        )


def reserve_seats(flight_id: str, class_id: str, count: int) -> None:
    with transaction():
        fare = get_fare(flight_id, class_id)
        ensure_seats(fare, count)
        db.fares.update(fare["fare_id"], {"available_seats": fare["available_seats"] - count})


def release_seats(flight_id: str, class_id: str, count: int) -> None:
    with transaction():
        fare = db.fares.find_one(flight_id=flight_id, class_id=class_id)
        if fare:
            available = min(fare["total_seats"], fare["available_seats"] + count)
            db.fares.update(fare["fare_id"], {"available_seats": available})


# SSR pricing

def get_ssr_catalog_item(ssr_type: str) -> dict:
    item = db.ssr_catalog.get(ssr_type)
    if not item:
        raise NotFoundError(f"SSR type {ssr_type} not found.")
    return item


def ssr_price(ssr_type: str, quantity: int = 1, tier: dict | None = None) -> dict:
    item = get_ssr_catalog_item(ssr_type)
    discount = 0.0
    if tier:
        discount = 100.0 if ssr_type in tier["free_ssrs"] else tier["ssr_discount_percent"]
    price = round(item["price"] * quantity * (1 - discount / 100), 2)
    return {
        "ssr_type": ssr_type,
        "name": item["name"],
        "unit_price": item["price"],
        "quantity": quantity,
        "discount_percent": discount,
        "price": price,
        "currency": item["currency"],
        "tier_id": tier["tier_id"] if tier else None,
        "eligible": (ssr_type in tier["eligible_ssrs"]) if tier else None,
    }
