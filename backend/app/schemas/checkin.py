from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, CheckinStatus, Direction
from app.schemas.booking import BookingView
from app.schemas.ticket import BoardingPass


class CheckinLookup(BaseModel):
    pnr: str = Field(min_length=6, max_length=6, examples=["AB12CD"])
    last_name: str = Field(min_length=1, examples=["Smith"])


class CheckinValidateRequest(CheckinLookup):
    direction: Direction | None = Field(default=None, description="Journey to check in. Defaults to the next upcoming journey.")


class CheckinCreate(CheckinValidateRequest):
    passenger_ids: list[str] | None = Field(
        default=None, description="Passengers to check in. Defaults to every eligible passenger."
    )


class CheckinValidation(BaseModel):
    booking: BookingView
    direction: Direction | None
    flight_ids: list[str] = Field(description="Remaining segments of the journey that check-in covers")
    can_check_in: bool
    eligible_passenger_ids: list[str]
    reasons: list[str] = Field(description="Why some or all passengers cannot check in")


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
    direction: Direction | None
    checkins: list[Checkin]
    boarding_passes: list[BoardingPass]
