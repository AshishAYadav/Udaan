from datetime import date

from fastapi import APIRouter, Query, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.models.enums import CabinClass, FlightStatus
from app.schemas.flight import (
    Flight,
    FlightScheduleCreate,
    FlightSchedulePage,
    FlightScheduleUpdate,
    FlightSearchResult,
    FlightSchedule,
)
from app.services import flight_service

router = APIRouter(prefix="/flights", tags=["Flights"])


@router.get("/search", response_model=list[FlightSearchResult], responses=error_responses(400, 404, auth=False),
            summary="Search direct flights",
            description="Direct flights only; use `/api/itineraries/search` for connections and round trips. Bookable flights (SCHEDULED/DELAYED, not departed) from `origin` to "
                        "`destination` on the given local departure date, with cabins that have at least "
                        "`passengers` seats. Each result lists available cabins and the starting fare.")
def search_flights(
    origin: str = Query(..., min_length=3, max_length=3, description="Origin IATA code", examples=["DXB"]),
    destination: str = Query(..., min_length=3, max_length=3, description="Destination IATA code", examples=["LHR"]),
    date: date = Query(..., description="Local departure date (YYYY-MM-DD)"),
    cabin_class: CabinClass | None = Query(None, description="Only return this cabin"),
    passengers: int = Query(1, ge=1, le=9, description="Seats required"),
):
    return flight_service.search_flights(origin, destination, date, cabin_class, passengers)


@router.get("", response_model=list[Flight], responses=error_responses(auth=False), summary="List flights",
            description="Raw flight records filtered by route, local date range, status or aircraft, sorted by departure.")
def list_flights(
    origin: str | None = None,
    destination: str | None = None,
    date_from: date | None = Query(None, description="Earliest local departure date"),
    date_to: date | None = Query(None, description="Latest local departure date"),
    status: FlightStatus | None = None,
    aircraft_id: str | None = None,
    upcoming_only: bool = Query(False, description="Exclude flights that have departed"),
    limit: int = Query(100, ge=1, le=1000),
):
    flights = flight_service.list_flights(origin, destination, date_from, date_to, status, aircraft_id, upcoming_only)
    return flights[:limit]


@router.get("/schedules", response_model=FlightSchedulePage, responses=error_responses(), summary="Get flight schedules (admin)",
            description="Paginated flight schedules for administration, including aircraft, capacity, seats sold "
                        "and seats available.")
def list_schedules(
    origin: str | None = None,
    destination: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: FlightStatus | None = None,
    aircraft_id: str | None = None,
    upcoming_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = require("admin"),
):
    return flight_service.list_schedules(
        limit, offset, origin=origin, destination=destination, date_from=date_from, date_to=date_to,
        status=status, aircraft_id=aircraft_id, upcoming_only=upcoming_only,
    )


@router.post("/schedules", response_model=FlightSchedule, status_code=status.HTTP_201_CREATED,
             responses=error_responses(400, 404, 409), summary="Create a flight schedule (admin)",
             description="Create a dated flight on an active route. Arrival is calculated from the route duration in "
                         "the destination timezone. Fares are created for every cabin on the aircraft.\n\n"
                         "Rejected with **409** when the aircraft is still busy: an aircraft is busy from departure "
                         "until arrival plus minimum ground time (4 h domestic, 8 h international). Also rejected when "
                         "the flight number already operates that day. Requires `flights:write`.")
def create_schedule(payload: FlightScheduleCreate, _: Principal = require("flights:write")):
    return flight_service.create_schedule(payload)


@router.put("/schedules/{flight_id}", response_model=FlightSchedule, responses=error_responses(400, 404, 409),
            summary="Modify a flight schedule (admin)",
            description="Change flight number, aircraft, departure time or status. Retiming or re-assigning the "
                        "aircraft re-checks the aircraft rotation rule. A smaller aircraft must still hold the seats already "
                        "sold. Requires `flights:write`.")
def modify_schedule(flight_id: str, payload: FlightScheduleUpdate, _: Principal = require("flights:write")):
    return flight_service.modify_schedule(flight_id, payload)


@router.get("/{flight_id}", response_model=FlightSchedule, responses=error_responses(404, auth=False), summary="Get a flight",
            description="One flight with aircraft and seat availability.")
def get_flight(flight_id: str):
    return flight_service.get_schedule(flight_id)
