from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import PassengerType, PaymentAttemptResult, PaymentStatus


class TripSelection(BaseModel):
    outbound_flight_ids: list[str] = Field(
        min_length=1, max_length=2, description="Outbound journey: one flight, or two connecting flights",
        examples=[["FLT001"]],
    )
    return_flight_ids: list[str] = Field(
        default_factory=list, max_length=2, description="Return journey (empty for one-way)", examples=[[]]
    )


class CheckoutOptions(BaseModel):
    """Options for the hosted payment session (as in Stripe Checkout)."""

    currency: str | None = Field(default=None, description="Currency to charge, e.g. INR. Default USD.", examples=["USD"])
    client_reference_id: str | None = Field(
        default=None, max_length=200,
        description="Your own reference (e.g. a chat/conversation id). Echoed in webhooks so you can correlate them.",
    )
    metadata: dict[str, str] = Field(default_factory=dict, description="Free-form key/values echoed in webhooks")
    success_url: str | None = Field(default=None, description="Where the hosted page sends the payer after success")
    cancel_url: str | None = Field(default=None, description="Where the hosted page sends the payer on cancel")


class PaymentCard(BaseModel):
    brand: str
    last4: str
    holder_name: str


class FareLine(BaseModel):
    passenger_id: str
    passenger_type: PassengerType
    flight_id: str
    amount: float = Field(description="Base currency")


class PaymentSessionSummary(BaseModel):
    payment_id: str
    session_id: str = Field(description="Secret handle of the hosted payment page")
    payment_url: str = Field(description="Send the payer here to complete payment")
    status: PaymentStatus
    amount: float
    currency: str
    base_amount: float
    base_currency: str
    expires_at: datetime
    client_reference_id: str | None = None


class Payment(PaymentSessionSummary):
    booking_id: str
    pnr: str
    user_id: str | None
    exchange_rate: float
    breakdown: list[FareLine]
    metadata: dict[str, Any]
    success_url: str | None = None
    cancel_url: str | None = None
    card: PaymentCard | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PaymentAttempt(BaseModel):
    attempt_id: str
    payment_id: str
    result: PaymentAttemptResult
    reason: str | None
    card: PaymentCard
    created_at: datetime


class CardDetails(BaseModel):
    card_number: str = Field(min_length=11, max_length=23, examples=["4111 1111 1111 1111"])
    expiry: str = Field(description="MMYY or MM/YY, in the future", examples=["1230"])
    cvv: str = Field(min_length=3, max_length=4, examples=["123"])
    holder_name: str = Field(min_length=1, max_length=80, examples=["JOHN SMITH"])


class PaymentSessionPublic(BaseModel):
    """What the hosted payment page shows."""

    session_id: str
    status: PaymentStatus
    merchant: str
    description: str
    pnr: str
    amount: float
    currency: str
    base_amount: float
    base_currency: str
    expires_at: datetime
    passengers: int
    itinerary: list[str]
    card: PaymentCard | None = None
    success_url: str | None = None
    cancel_url: str | None = None


class PaymentResult(PaymentSessionPublic):
    booking_id: str
    redirect_url: str | None = Field(default=None, description="success_url with session_id, pnr and status appended")
