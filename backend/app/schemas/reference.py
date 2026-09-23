"""Reference data: airports, routes, aircraft, cabin classes, tiers, users."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, Role, SSRType


class Airport(BaseModel):
    airport_id: str = Field(examples=["DXB"])
    iata_code: str = Field(examples=["DXB"])
    name: str
    city: str
    country: str
    timezone: str = Field(examples=["Asia/Dubai"])


class Route(BaseModel):
    route_id: str = Field(examples=["RT001"])
    origin: str = Field(examples=["DXB"])
    destination: str = Field(examples=["LHR"])
    duration_minutes: int
    distance_km: int
    active: bool


class RouteDetail(Route):
    origin_airport: Airport
    destination_airport: Airport


class Aircraft(BaseModel):
    aircraft_id: str = Field(examples=["AC001"])
    registration: str = Field(examples=["VT-UDA"])
    model: str = Field(examples=["A350-900"])
    total_seats: int
    cabin_configuration: dict[CabinClass, int]
    bassinet_positions: int


class CabinClassInfo(BaseModel):
    class_id: CabinClass
    name: str
    description: str
    rank: int = Field(description="1 = lowest cabin")
    baggage_allowance_kg: int


class AvailableCabinClass(CabinClassInfo):
    fare_id: str
    price: float = Field(description="Adult base fare")
    currency: str
    available_seats: int


class Tier(BaseModel):
    tier_id: str = Field(examples=["GOLD"])
    name: str
    priority: int
    eligible_ssrs: list[SSRType]
    free_ssrs: list[SSRType]
    ssr_discount_percent: float
    extra_baggage_kg: int
    benefits: list[str]


class User(BaseModel):
    user_id: str = Field(examples=["USR001"])
    username: str = Field(examples=["john"])
    role: Role
    first_name: str
    last_name: str
    email: str
    phone: str
    tier_id: str | None = Field(default=None, description="Membership tier; admins have none")
    created_at: datetime


class UserDetail(User):
    tier: Tier | None = None


class AdminSummary(BaseModel):
    airports: int
    routes: int
    aircraft: int
    flights_total: int
    flights_upcoming: int
    users: int
    passengers: int
    bookings_total: int
    bookings_active: int
    checkins: int
    tickets_issued: int
