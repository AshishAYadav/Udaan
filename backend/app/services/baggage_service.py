"""Standard baggage allowances by route type, cabin and passenger type.

A journey is domestic only when every segment is domestic. Members get their tier's
extra checked baggage (seated passengers only). Infants have cabin baggage only.
"""
from app.models.enums import CabinClass, PassengerType

# cabin -> (checked pieces, kg per checked piece, cabin pieces, kg per cabin piece)
DOMESTIC = {
    CabinClass.ECONOMY: (1, 15, 1, 7),
    CabinClass.PREMIUM_ECONOMY: (1, 20, 1, 7),
    CabinClass.BUSINESS: (1, 30, 2, 7),
    CabinClass.FIRST: (1, 35, 2, 7),
}
INTERNATIONAL = {
    CabinClass.ECONOMY: (1, 25, 1, 7),
    CabinClass.PREMIUM_ECONOMY: (2, 23, 1, 7),
    CabinClass.BUSINESS: (2, 32, 2, 7),
    CabinClass.FIRST: (3, 32, 2, 7),
}
INFANT_CABIN_KG = 5


def allowance(domestic: bool, class_id: str, passenger_type: str, tier: dict | None = None) -> dict:
    checked_pieces, checked_kg, cabin_pieces, cabin_kg = (DOMESTIC if domestic else INTERNATIONAL)[CabinClass(class_id)]
    notes = ["One personal item (handbag or laptop bag) in addition to cabin baggage."]
    if passenger_type == PassengerType.INFANT:
        return {
            "passenger_type": passenger_type,
            "checked_pieces": 0,
            "checked_kg": 0,
            "cabin_pieces": 1,
            "cabin_kg": INFANT_CABIN_KG,
            "personal_item": False,
            "tier_bonus_kg": 0,
            "notes": ["Infant bag up to 5 kg in the cabin.", "One collapsible stroller or car seat is carried free."],
        }
    bonus = (tier or {}).get("extra_baggage_kg", 0)
    if bonus:
        notes.append(f"Includes {bonus} kg {tier['name']} member bonus.")
    return {
        "passenger_type": passenger_type,
        "checked_pieces": checked_pieces,
        "checked_kg": checked_pieces * checked_kg + bonus,
        "cabin_pieces": cabin_pieces,
        "cabin_kg": cabin_kg,
        "personal_item": True,
        "tier_bonus_kg": bonus,
        "notes": notes,
    }


def for_party(domestic: bool, class_id: str, tier: dict | None = None) -> dict[str, dict]:
    return {t.value: allowance(domestic, class_id, t, tier) for t in PassengerType}


def policy_table() -> list[dict]:
    """The full allowance matrix, for help pages and API clients."""
    return [
        {"route_type": route, "class_id": cabin.value, **{t.value: allowance(route == "DOMESTIC", cabin, t) for t in PassengerType}}
        for route in ("DOMESTIC", "INTERNATIONAL")
        for cabin in CabinClass
    ]
