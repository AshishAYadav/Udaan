from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, CheckinStatus, Direction, FlightPhase
from app.schemas.booking import BookingView
from app.schemas.ticket import BoardingPass


class CheckinLookup(BaseModel):
    pnr: str = Field(min_length=6, max_length=6, examples=["AB12CD"])
    last_name: str = Field(min_length=1, examples=["Smith"])


class CheckinCreate(CheckinLookup):
    flight_ids: list[str] | None = Field(
        default=None, description="Flights (segments) to check in. Default: every flight whose check-in window is open."
    )
    passenger_ids: list[str] | None = Field(
        default=None, description="Passengers to check in. Default: everyone not yet checked in on those flights."
    )


class SegmentCheckinPassenger(BaseModel):
    passenger_id: str
    checked_in: bool
    eligible: bool
    reason: str | None = None
    travels_with: str | None = Field(default=None, description="Infant/adult partner who must check in together")


class SegmentCheckinStatus(BaseModel):
    segment_no: int
    direction: Direction
    flight_id: str
    flight_number: str
    phase: FlightPhase
    checkin_opens_at: datetime
    checkin_closes_at: datetime
    open: bool
    reason: str | None = None
    passengers: list[SegmentCheckinPassenger]


class CheckinValidation(BaseModel):
    booking: BookingView
    segments: list[SegmentCheckinStatus]
    can_check_in: bool
    reasons: list[str] = Field(description="Why some flights cannot be checked in now")


class CheckinUpdate(BaseModel):
    seat: str | None = Field(default=None, pattern=r"^\d{1,2}[A-K]$", examples=["22C"])
    status: CheckinStatus | None = Field(
        default=None, description="Set NOT_CHECKED_IN to offload the passenger (cancels the ticket)."
    )


class Checkin(BaseModel):
    checkin_id: str = Field(examples=["CHK001"])
    booking_id: str
    pnr: str
    passenger_id: str
    flight_id: str
    class_id: CabinClass
    seat: str
    sequence_number: int
    status: CheckinStatus
    ticket_id: str | None = None
    checked_in_at: datetime
    updated_at: datetime | None = None


class CheckinResult(BaseModel):
    booking_id: str
    pnr: str
    checkins: list[Checkin]
    boarding_passes: list[BoardingPass]
