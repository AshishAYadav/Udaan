from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    BookingStatus,
    CabinClass,
    CheckinStatus,
    Direction,
    Gender,
    PassengerType,
    PaymentStatus,
    TicketStatus,
    TripType,
)
from app.schemas.flight import FlightSummary
from app.schemas.payment import TripSelection
from app.schemas.ssr import SSR


class BookingCreate(TripSelection):
    user_id: str | None = Field(default=None, description="Admins only: book on behalf of this user")
    class_id: CabinClass = CabinClass.ECONOMY
    passenger_ids: list[str] = Field(min_length=1, examples=[["PAX001"]])
    payment_id: str = Field(description="A COMPLETED payment created for exactly these flights, cabin and passengers")
    payment_key: str | None = Field(default=None, description="Guests: the payment's access_key (not needed when logged in)")
    contact_email: str | None = None
    contact_phone: str | None = None


class BookingUpdate(BaseModel):
    contact_email: str | None = None
    contact_phone: str | None = None


class BookingChangeRequest(BaseModel):
    direction: Direction = Field(default=Direction.OUTBOUND, description="Journey to replace")
    new_flight_ids: list[str] = Field(min_length=1, max_length=2, examples=[["FLT011"]])


class BookingCancelRequest(BaseModel):
    reason: str | None = None


class Segment(BaseModel):
    segment_no: int
    flight_id: str
    direction: Direction


class Booking(BaseModel):
    booking_id: str = Field(examples=["BK001"])
    pnr: str = Field(examples=["AB12CD"])
    user_id: str | None = Field(description="Owner account; null for guest bookings")
    trip_type: TripType
    segments: list[Segment]
    class_id: CabinClass
    passenger_ids: list[str]
    payment_id: str
    total_amount: float
    currency: str
    status: BookingStatus
    contact_email: str | None = None
    contact_phone: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    cancelled_at: datetime | None = None


class BookingPassenger(BaseModel):
    passenger_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    passenger_type: PassengerType


class SegmentPassenger(BaseModel):
    passenger_id: str
    checkin_status: CheckinStatus
    checkin_id: str | None = None
    seat: str | None = None
    ticket_status: TicketStatus
    ticket_id: str | None = None
    ticket_number: str | None = None


class SegmentView(Segment):
    flight: FlightSummary
    passengers: list[SegmentPassenger]


class PaymentBrief(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount: float
    currency: str


class BookingView(BaseModel):
    """Booking with segments, passengers, payment, check-in and ticket status resolved."""

    booking_id: str
    pnr: str
    status: BookingStatus
    trip_type: TripType
    user_id: str | None
    class_id: CabinClass
    cabin_name: str
    total_amount: float
    currency: str
    contact_email: str | None = None
    contact_phone: str | None = None
    created_at: datetime
    segments: list[SegmentView]
    passengers: list[BookingPassenger]
    payment: PaymentBrief
    ssrs: list[SSR]


class BookingHistoryEntry(BaseModel):
    history_id: str
    booking_id: str
    action: str
    details: dict[str, Any]
    created_at: datetime


class BookingChangeResult(BaseModel):
    booking: BookingView
    direction: Direction
    previous_flight_ids: list[str]
    fare_difference: float = Field(description="New fare minus old fare (informational in the sandbox)")
    currency: str
