from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, FlightStatus
from app.schemas.common import AirportBrief


class Flight(BaseModel):
    flight_id: str = Field(examples=["FLT001"])
    flight_number: str = Field(examples=["UD101"])
    route_id: str
    aircraft_id: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime = Field(description="Local time at the departure airport, with offset")
    arrival_time: datetime = Field(description="Local time at the arrival airport, with offset")
    departure_date: date = Field(description="Local departure date (used by search)")
    duration_minutes: int
    status: FlightStatus
    created_at: datetime
    updated_at: datetime | None = None


class ClassAvailability(BaseModel):
    class_id: CabinClass
    name: str
    fare_id: str
    price: float
    currency: str
    available_seats: int


class FlightSummary(BaseModel):
    flight_id: str
    flight_number: str
    origin: AirportBrief
    destination: AirportBrief
    departure: datetime
    arrival: datetime
    duration_minutes: int
    status: FlightStatus
    aircraft_model: str


class FlightSearchResult(FlightSummary):
    available_classes: list[ClassAvailability]
    starting_fare: float
    currency: str
    available_seats: int


class FlightSchedule(Flight):
    aircraft_registration: str
    aircraft_model: str
    capacity: int
    seats_sold: int
    available_seats: int


class FlightSchedulePage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[FlightSchedule]


class FlightScheduleCreate(BaseModel):
    flight_number: str = Field(pattern=r"^[A-Z0-9]{2}\d{1,4}$", examples=["UD901"])
    route_id: str = Field(examples=["RT001"])
    aircraft_id: str = Field(examples=["AC001"])
    departure_time: datetime = Field(
        description="Departure time. A value without offset is interpreted as local time at the origin airport.",
        examples=["2026-11-30T10:00:00"],
    )
    fares: dict[CabinClass, float] | None = Field(
        default=None,
        description="Optional adult base fare per cabin. Cabins not supplied get a default price.",
        examples=[{"ECONOMY": 420.0, "BUSINESS": 1500.0}],
    )


class FlightScheduleUpdate(BaseModel):
    flight_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}\d{1,4}$")
    aircraft_id: str | None = None
    departure_time: datetime | None = Field(
        default=None, description="New departure time (naive = origin local time)."
    )
    status: FlightStatus | None = None
