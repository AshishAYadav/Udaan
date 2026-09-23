from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PassengerType, SSRStatus, SSRType


class SSRCatalogItem(BaseModel):
    ssr_type: SSRType
    name: str
    description: str
    price: float = Field(description="Undiscounted unit price")
    currency: str
    options: list[str]
    max_quantity: int
    required_passenger_type: PassengerType | None = None
    min_flight_minutes: int | None = None


class SSRCreate(BaseModel):
    booking_id: str = Field(examples=["BK001"])
    passenger_id: str = Field(examples=["PAX001"])
    flight_id: str | None = Field(default=None, description="Segment flight. Defaults to the first segment not yet departed.")
    type: SSRType
    quantity: int = Field(default=1, ge=1, le=10, description="Units, e.g. 5 kg blocks of excess baggage")
    option: str | None = Field(default=None, description="Option code, e.g. meal VGML or wheelchair WCHR")
    notes: str | None = None


class SSR(BaseModel):
    ssr_id: str = Field(examples=["SSR001"])
    booking_id: str
    passenger_id: str
    flight_id: str
    type: SSRType
    option: str | None = None
    quantity: int
    price: float
    currency: str
    status: SSRStatus
    notes: str | None = None
    created_at: datetime
    cancelled_at: datetime | None = None


class SSRAvailability(BaseModel):
    ssr_type: SSRType
    name: str
    description: str
    flight_id: str
    eligible: bool
    reason: str | None = Field(default=None, description="Why the SSR is unavailable, if not eligible")
    unit_price: float
    currency: str
    options: list[str]
