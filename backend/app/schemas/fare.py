from pydantic import BaseModel, Field

from app.models.enums import CabinClass, SSRType


class Fare(BaseModel):
    fare_id: str = Field(examples=["FARE001"])
    flight_id: str
    class_id: CabinClass
    fare_type: str = Field(examples=["STANDARD"])
    base_price: float = Field(description="Adult fare")
    child_price: float | None = Field(default=None, description="Child fare (75% of adult)")
    infant_price: float | None = Field(default=None, description="Infant fare (10% of adult, on lap)")
    currency: str
    total_seats: int
    available_seats: int


class SSRFareQuote(BaseModel):
    ssr_type: SSRType
    name: str
    unit_price: float
    quantity: int
    discount_percent: float
    price: float = Field(description="Final price after tier discounts")
    currency: str
    tier_id: str | None = None
    eligible: bool | None = Field(default=None, description="Tier eligibility, when a tier or user is supplied")
