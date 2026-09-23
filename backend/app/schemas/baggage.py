from pydantic import BaseModel, Field

from app.models.enums import CabinClass, PassengerType


class BaggageAllowance(BaseModel):
    passenger_type: PassengerType
    checked_pieces: int
    checked_kg: int = Field(description="Total checked weight across all pieces")
    cabin_pieces: int
    cabin_kg: int = Field(description="Weight per cabin piece")
    personal_item: bool = Field(description="A handbag/laptop bag is allowed in addition to cabin baggage")
    tier_bonus_kg: int = 0
    notes: list[str]


class BaggagePolicyRow(BaseModel):
    route_type: str = Field(examples=["DOMESTIC"])
    class_id: CabinClass
    ADULT: BaggageAllowance
    CHILD: BaggageAllowance
    INFANT: BaggageAllowance
