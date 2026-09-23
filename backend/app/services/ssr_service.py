"""Special service requests, per passenger and flight segment.

Authorisation is layered:
1. the token must carry `ssr:write` and `ssr:<TYPE>` (granted from the user's tier at login);
2. the booking owner's *current* tier must still be eligible (tokens can be stale);
3. passenger, flight and capacity rules.
"""
from app.auth.dependencies import Principal
from app.db.database import next_id, transaction
from app.db.database import repositories as db
from app.models.enums import ACTIVE_BOOKING_STATUSES, SSRStatus, SSRType
from app.services import booking_service, fare_service, flight_service
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.utils.timeutils import now_iso


def list_catalog() -> list[dict]:
    return sorted(db.ssr_catalog.all(), key=lambda s: s["ssr_type"])


def get_ssr(ssr_id: str, actor: Principal) -> dict:
    ssr = db.ssrs.get(ssr_id)
    booking = db.bookings.get(ssr["booking_id"]) if ssr else None
    if not booking or not actor.owns(booking["user_id"]):
        raise NotFoundError(f"SSR {ssr_id} not found.")
    return ssr


def list_ssrs(
    actor: Principal,
    booking_id: str | None = None,
    passenger_id: str | None = None,
    flight_id: str | None = None,
    status: SSRStatus | None = None,
) -> list[dict]:
    owned = None if actor.is_admin else {b["booking_id"] for b in db.bookings.find(user_id=actor.user_id)}

    def matches(s: dict) -> bool:
        return (
            (owned is None or s["booking_id"] in owned)
            and (not booking_id or s["booking_id"] == booking_id)
            and (not passenger_id or s["passenger_id"] == passenger_id)
            and (not flight_id or s["flight_id"] == flight_id)
            and (not status or s["status"] == status)
        )

    return sorted(db.ssrs.filter(matches), key=lambda s: s["ssr_id"])


def _context(booking_id: str, passenger_id: str, flight_id: str | None, actor: Principal) -> tuple[dict, dict, dict, dict]:
    booking = booking_service.get_manageable_booking(booking_id, actor)
    if booking["status"] not in ACTIVE_BOOKING_STATUSES:
        raise ConflictError(f"Booking {booking['pnr']} is {booking['status']}.")
    if passenger_id not in booking["passenger_ids"]:
        raise BadRequestError(f"Passenger {passenger_id} is not on booking {booking_id}.")
    passenger = db.passengers.get(passenger_id)
    if not passenger:
        raise NotFoundError(f"Passenger {passenger_id} not found.")

    segment_flights = [flight_service.get_flight(fid) for fid in booking_service.flight_ids(booking)]
    if flight_id:
        flight = next((f for f in segment_flights if f["flight_id"] == flight_id), None)
        if not flight:
            raise BadRequestError(f"Flight {flight_id} is not a segment of booking {booking_id}.")
    else:
        flight = next((f for f in segment_flights if not flight_service.has_departed(f)), segment_flights[-1])
    if flight_service.has_departed(flight):
        raise BadRequestError("SSRs cannot be requested after departure.")
    # Guest bookings have no member tier, so no SSR is eligible for them.
    tier = (ref.get_user(booking["user_id"])["tier"] or {}) if booking["user_id"] else {}
    return booking, passenger, flight, tier


def _ineligibility_reason(item: dict, booking: dict, passenger: dict, flight: dict, tier: dict, quantity: int = 1) -> str | None:
    ssr_type = item["ssr_type"]
    if not tier:
        return "Special services need a member booking. Log in and book with your account to add them."
    if ssr_type not in tier.get("eligible_ssrs", []):
        return f"{item['name']} is not available for {tier['name']} tier members."
    required_type = item.get("required_passenger_type")
    if required_type and passenger["passenger_type"] != required_type:
        return f"{item['name']} is only available for {required_type.lower()} passengers."
    min_minutes = item.get("min_flight_minutes")
    if min_minutes and flight["duration_minutes"] < min_minutes:
        return f"{item['name']} is only offered on flights longer than {min_minutes} minutes."
    if quantity > item["max_quantity"]:
        return f"{item['name']} allows at most {item['max_quantity']} unit(s)."
    if db.ssrs.find_one(
        passenger_id=passenger["passenger_id"], booking_id=booking["booking_id"], flight_id=flight["flight_id"],
        type=ssr_type, status=SSRStatus.CONFIRMED.value,
    ):
        return f"{item['name']} is already confirmed for this passenger on this flight."
    if ssr_type == SSRType.BASSINET:
        positions = (db.aircrafts.get(flight["aircraft_id"]) or {}).get("bassinet_positions", 0)
        used = len(db.ssrs.find(flight_id=flight["flight_id"], type=SSRType.BASSINET.value, status=SSRStatus.CONFIRMED.value))
        if used >= positions:
            return "No bassinet positions remain on this flight."
    return None


def available_ssrs(booking_id: str, passenger_id: str, flight_id: str | None, actor: Principal) -> list[dict]:
    booking, passenger, flight, tier = _context(booking_id, passenger_id, flight_id, actor)
    result = []
    for item in list_catalog():
        reason = _ineligibility_reason(item, booking, passenger, flight, tier)
        result.append(
            {
                "ssr_type": item["ssr_type"],
                "name": item["name"],
                "description": item["description"],
                "flight_id": flight["flight_id"],
                "eligible": reason is None,
                "reason": reason,
                "unit_price": fare_service.ssr_price(item["ssr_type"], 1, tier or None)["price"],
                "currency": item["currency"],
                "options": item["options"],
            }
        )
    return result


def create_ssr(data, actor: Principal) -> dict:
    if not actor.has(f"ssr:{data.type.value}"):
        raise ForbiddenError(f"Your access token does not permit {data.type.value} requests (not included in your tier).")
    with transaction():
        booking, passenger, flight, tier = _context(data.booking_id, data.passenger_id, data.flight_id, actor)
        item = fare_service.get_ssr_catalog_item(data.type)
        reason = _ineligibility_reason(item, booking, passenger, flight, tier, data.quantity)
        if reason:
            raise BadRequestError(reason)

        option = data.option
        if item["options"]:
            option = option or item["options"][0]
            if option not in item["options"]:
                raise BadRequestError(f"Invalid option {option} for {item['name']}. Choose one of {', '.join(item['options'])}.")
        elif option:
            raise BadRequestError(f"{item['name']} does not take an option.")

        price = fare_service.ssr_price(data.type, data.quantity, tier)
        ssr = {
            "ssr_id": next_id("SSR"),
            "booking_id": booking["booking_id"],
            "passenger_id": passenger["passenger_id"],
            "flight_id": flight["flight_id"],
            "type": data.type.value,
            "option": option,
            "quantity": data.quantity,
            "price": price["price"],
            "currency": price["currency"],
            "status": SSRStatus.CONFIRMED.value,
            "notes": data.notes,
            "created_at": now_iso(),
            "cancelled_at": None,
        }
        return db.ssrs.insert(ssr)


def cancel_ssr(ssr_id: str, actor: Principal) -> dict:
    ssr = get_ssr(ssr_id, actor)
    if ssr["status"] == SSRStatus.CANCELLED:
        raise ConflictError(f"SSR {ssr_id} is already cancelled.")
    return db.ssrs.update(ssr_id, {"status": SSRStatus.CANCELLED.value, "cancelled_at": now_iso()})
