from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.reference import Aircraft
from app.services import aircraft_service
from app.services import reference_service as ref
from app.utils.timeutils import in_timezone

router = APIRouter(prefix="/aircrafts", tags=["Aircraft"])


@router.get("", response_model=list[Aircraft], responses=error_responses(), summary="List aircraft (admin)",
            description="Fleet with cabin configuration and bassinet positions.")
def list_aircraft(_: Principal = require("admin")):
    return aircraft_service.list_aircraft()


@router.get("/available", response_model=list[Aircraft], responses=error_responses(404),
            summary="Aircraft available for a flight (admin)",
            description="Aircraft free to operate `route_id` departing at `departure_time`. An aircraft is busy from "
                        "departure until arrival plus minimum ground time (4 h domestic, 8 h international).")
def available_aircraft(
    route_id: str = Query(..., examples=["RT001"]),
    departure_time: datetime = Query(..., description="Departure; a value without offset is origin local time"),
    _: Principal = require("admin"),
):
    route = ref.get_route(route_id)
    origin, destination = ref.get_airport(route["origin"]), ref.get_airport(route["destination"])
    departure = in_timezone(departure_time, origin["timezone"])
    arrival = departure + timedelta(minutes=route["duration_minutes"])
    return aircraft_service.available_aircraft(departure, arrival, origin["country"] == destination["country"])


@router.get("/{aircraft_id}", response_model=Aircraft, responses=error_responses(404), summary="Get an aircraft (admin)")
def get_aircraft(aircraft_id: str, _: Principal = require("admin")):
    return aircraft_service.get_aircraft(aircraft_id)
