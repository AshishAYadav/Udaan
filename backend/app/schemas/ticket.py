from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CabinClass, FlightPhase, PassengerType, TicketStatus
from app.schemas.baggage import BaggageAllowance
from app.schemas.common import AirportBrief


class TicketCreate(BaseModel):
    checkin_id: str = Field(examples=["CHK001"])


class Ticket(BaseModel):
    ticket_id: str = Field(examples=["TKT001"])
    ticket_number: str = Field(examples=["7750000000001"])
    checkin_id: str
    booking_id: str
    pnr: str
    passenger_id: str
    flight_id: str
    class_id: CabinClass
    seat: str
    status: TicketStatus
    issued_at: datetime
    cancelled_at: datetime | None = None


class BoardingPass(BaseModel):
    ticket_id: str
    ticket_number: str
    status: TicketStatus
    airline: str
    pnr: str
    passenger_name: str
    passenger_type: PassengerType
    flight_number: str
    origin: AirportBrief
    destination: AirportBrief
    departure_time: datetime
    arrival_time: datetime
    departure_date: str = Field(examples=["01 Oct 2026"])
    departure_local_time: str = Field(examples=["08:00"])
    boarding_time: str = Field(examples=["07:15"])
    gate: str
    cabin: CabinClass
    cabin_name: str
    seat: str
    sequence_number: int
    phase: FlightPhase
    baggage: BaggageAllowance
