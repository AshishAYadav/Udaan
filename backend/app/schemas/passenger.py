from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import Gender, PassengerType


class PassengerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50, examples=["John"])
    last_name: str = Field(min_length=1, max_length=50, examples=["Smith"])
    date_of_birth: date = Field(examples=["1990-01-01"])
    gender: Gender
    passenger_type: PassengerType | None = Field(
        default=None,
        description="Optional. Derived from date of birth (<2 infant, <12 child); rejected if inconsistent.",
    )
    user_id: str | None = Field(default=None, description="Owning user account, if any")
    accompanying_adult_id: str | None = Field(
        default=None, description="Infants only: the adult passenger travelling with the infant"
    )
    email: str | None = None
    phone: str | None = None


class PassengerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    date_of_birth: date | None = None
    gender: Gender | None = None
    accompanying_adult_id: str | None = None
    email: str | None = None
    phone: str | None = None


class Passenger(BaseModel):
    passenger_id: str = Field(examples=["PAX001"])
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    passenger_type: PassengerType
    user_id: str | None = None
    accompanying_adult_id: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
