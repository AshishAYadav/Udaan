from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, PassengerType, PaymentAction, PaymentStatus


class TripSelection(BaseModel):
    outbound_flight_ids: list[str] = Field(
        min_length=1, max_length=2, description="Outbound journey: one flight, or two connecting flights",
        examples=[["FLT001"]],
    )
    return_flight_ids: list[str] = Field(
        default_factory=list, max_length=2, description="Return journey (empty for one-way)", examples=[[]]
    )


class PaymentCreate(TripSelection):
    user_id: str | None = Field(
        default=None, description="Admins only: pay on behalf of this user. Customers pay for themselves; guests omit it."
    )
    class_id: CabinClass = CabinClass.ECONOMY
    passenger_ids: list[str] = Field(min_length=1, examples=[["PAX001"]])
    method: str = Field(default="MOCK_CARD", description="Mock payment method label. No card data is accepted.")


class PaymentUpdate(BaseModel):
    action: PaymentAction = Field(description="Mock gateway decision: APPROVE or REJECT")


class FareLine(BaseModel):
    passenger_id: str
    passenger_type: PassengerType
    flight_id: str
    amount: float


class Payment(BaseModel):
    payment_id: str = Field(examples=["PAY001"])
    user_id: str | None = Field(description="Paying account; null for guests")
    outbound_flight_ids: list[str]
    return_flight_ids: list[str]
    class_id: CabinClass
    passenger_ids: list[str]
    amount: float
    currency: str
    method: str
    status: PaymentStatus
    breakdown: list[FareLine]
    booking_id: str | None = None
    access_key: str = Field(description="Secret for guests: send as X-Payment-Key header and as payment_key when booking")
    created_at: datetime
    updated_at: datetime | None = None


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount: float
    currency: str
    booking_id: str | None
    can_create_booking: bool = Field(description="True when the payment is COMPLETED and not yet used")
