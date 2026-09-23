from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, TripType
from app.schemas.common import AirportBrief
from app.schemas.flight import FlightSummary


class ItineraryClass(BaseModel):
    class_id: CabinClass
    name: str
    price: float = Field(description="Adult fare summed over all segments")
    child_price: float = Field(description="Child fare (75%) summed over all segments")
    infant_price: float = Field(description="Infant fare (10%, on lap) summed over all segments")
    party_total: float = Field(description="Total for the searched adults, children and infants")
    currency: str
    available_seats: int = Field(description="Lowest availability across segments")


class Layover(BaseModel):
    airport: AirportBrief
    minutes: int


class Itinerary(BaseModel):
    itinerary_id: str = Field(examples=["FLT005-FLT002"])
    flight_ids: list[str]
    stops: int
    origin: AirportBrief
    destination: AirportBrief
    departure: datetime
    arrival: datetime
    total_duration_minutes: int
    segments: list[FlightSummary]
    layovers: list[Layover]
    available_classes: list[ItineraryClass]
    starting_fare: float
    currency: str


class PartySize(BaseModel):
    adults: int
    children: int
    infants: int


class TripSearchResult(BaseModel):
    trip_type: TripType
    party: PartySize
    outbound: list[Itinerary]
    return_: list[Itinerary] = Field(alias="return", serialization_alias="return")

    model_config = {"populate_by_name": True}
