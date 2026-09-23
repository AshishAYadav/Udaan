"""Passenger management and party (adult/child/infant) validation."""
from datetime import date

from app.auth.dependencies import Principal
from app.config import settings
from app.db.database import next_id
from app.db.database import repositories as db
from app.models.enums import HOLDING_BOOKING_STATUSES, PassengerType
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.utils.timeutils import age_on, now_iso


def classify(date_of_birth: date, on: date) -> PassengerType:
    age = age_on(date_of_birth, on)
    if age < settings.infant_max_age:
        return PassengerType.INFANT
    if age < settings.child_max_age:
        return PassengerType.CHILD
    return PassengerType.ADULT


def get_passenger(passenger_id: str, actor: Principal | None = None) -> dict:
    """Load a passenger; when an actor is given, customers may only see their own passengers."""
    passenger = db.passengers.get(passenger_id)
    if not passenger or (actor and not actor.owns(passenger.get("user_id"))):
        raise NotFoundError(f"Passenger {passenger_id} not found.")
    return passenger


def list_passengers(actor: Principal, user_id: str | None = None, last_name: str | None = None) -> list[dict]:
    if not actor.is_admin:
        user_id = actor.user_id

    def matches(p: dict) -> bool:
        return (not user_id or p.get("user_id") == user_id) and (
            not last_name or p["last_name"].lower() == last_name.lower()
        )

    return sorted(db.passengers.filter(matches), key=lambda p: p["passenger_id"])


def has_last_name(passenger_ids: list[str], last_name: str | None) -> bool:
    """True if any listed passenger has this last name (case-insensitive)."""
    if not last_name:
        return False
    wanted = last_name.strip().lower()
    return any((db.passengers.get(pid) or {}).get("last_name", "").strip().lower() == wanted for pid in passenger_ids)


def active_bookings_for(passenger_id: str) -> list[dict]:
    return db.bookings.filter(
        lambda b: passenger_id in b["passenger_ids"] and b["status"] in HOLDING_BOOKING_STATUSES
    )


def _validate_accompanying_adult(passenger_type: PassengerType, adult_id: str | None, actor: Principal | None) -> None:
    if not adult_id:
        return
    if passenger_type != PassengerType.INFANT:
        raise BadRequestError("Only infants can have an accompanying adult.")
    if get_passenger(adult_id, actor)["passenger_type"] != PassengerType.ADULT:
        raise BadRequestError(f"Accompanying passenger {adult_id} is not an adult.")


def create_passenger(data, actor: Principal | None) -> dict:
    """Guests create unowned passengers; customers own theirs; admins may assign any user."""
    if data.date_of_birth > date.today():
        raise BadRequestError("Date of birth cannot be in the future.")
    if actor is None:
        if data.user_id or data.accompanying_adult_id:
            raise ForbiddenError("Log in to link passengers to an account or to another passenger.")
    elif actor.is_admin:
        if data.user_id:
            ref.get_user(data.user_id)
    elif data.user_id and data.user_id != actor.user_id:
        raise ForbiddenError("Passengers can only be created for your own account.")
    else:
        data = data.model_copy(update={"user_id": actor.user_id})

    derived = classify(data.date_of_birth, date.today())
    if data.passenger_type and data.passenger_type != derived:
        raise BadRequestError(
            f"Passenger type {data.passenger_type} does not match date of birth (passenger is {derived})."
        )
    _validate_accompanying_adult(derived, data.accompanying_adult_id, actor)

    passenger = {
        **data.model_dump(mode="json", exclude={"passenger_type"}),
        "passenger_id": next_id("PAX"),
        "passenger_type": derived.value,
        "created_at": now_iso(),
        "updated_at": None,
    }
    return db.passengers.insert(passenger)


def update_passenger(passenger_id: str, data, actor: Principal) -> dict:
    passenger = get_passenger(passenger_id, actor)
    changes = data.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise BadRequestError("No changes supplied.")

    if "date_of_birth" in changes:
        dob = data.date_of_birth
        if dob > date.today():
            raise BadRequestError("Date of birth cannot be in the future.")
        new_type = classify(dob, date.today())
        if new_type != passenger["passenger_type"] and active_bookings_for(passenger_id):
            raise ConflictError("Passenger type cannot change while the passenger has an active booking.")
        changes["passenger_type"] = new_type.value

    passenger_type = PassengerType(changes.get("passenger_type", passenger["passenger_type"]))
    _validate_accompanying_adult(passenger_type, changes.get("accompanying_adult_id"), actor)
    changes["updated_at"] = now_iso()
    return db.passengers.update(passenger_id, changes)


def delete_passenger(passenger_id: str, actor: Principal) -> None:
    get_passenger(passenger_id, actor)
    if active_bookings_for(passenger_id):
        raise ConflictError(f"Passenger {passenger_id} has an active booking and cannot be deleted.")
    db.passengers.remove(passenger_id)


def validate_party(passenger_ids: list[str], travel_date: date) -> list[dict]:
    """Load the passengers of a booking and enforce party composition rules.

    The effective passenger type is the age on the travel date.
    """
    if len(set(passenger_ids)) != len(passenger_ids):
        raise BadRequestError("Duplicate passengers in request.")

    party = []
    for pid in passenger_ids:
        passenger = get_passenger(pid)
        party.append({**passenger, "passenger_type": classify(date.fromisoformat(passenger["date_of_birth"]), travel_date).value})

    counts = {t: sum(1 for p in party if p["passenger_type"] == t) for t in PassengerType}
    seated = counts[PassengerType.ADULT] + counts[PassengerType.CHILD]

    if counts[PassengerType.ADULT] == 0:
        raise BadRequestError("A booking must include at least one adult; unaccompanied children and infants are not supported.")
    if counts[PassengerType.INFANT] > counts[PassengerType.ADULT]:
        raise BadRequestError("Each infant must be accompanied by a separate adult.")
    if seated > settings.max_seats_per_booking:
        raise BadRequestError(f"A booking can include at most {settings.max_seats_per_booking} seated passengers.")

    party_ids = set(passenger_ids)
    adults = {p["passenger_id"] for p in party if p["passenger_type"] == PassengerType.ADULT}
    assigned: set[str] = set()
    for infant in (p for p in party if p["passenger_type"] == PassengerType.INFANT):
        adult_id = infant.get("accompanying_adult_id")
        if not adult_id:
            continue
        if adult_id not in party_ids or adult_id not in adults:
            raise BadRequestError(f"Infant {infant['passenger_id']}'s accompanying adult {adult_id} is not an adult on this booking.")
        if adult_id in assigned:
            raise BadRequestError(f"Adult {adult_id} is already accompanying another infant.")
        assigned.add(adult_id)
    return party
