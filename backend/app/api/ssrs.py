from fastapi import APIRouter, Query, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.models.enums import SSRStatus
from app.schemas.ssr import SSR, SSRAvailability, SSRCatalogItem, SSRCreate
from app.services import ssr_service

router = APIRouter(prefix="/ssrs", tags=["Special service requests"])


@router.get("", response_model=list[SSR], responses=error_responses(), summary="List SSRs",
            description="SSRs on your bookings (admins: all), filtered by booking, passenger, flight or status.")
def list_ssrs(
    booking_id: str | None = None,
    passenger_id: str | None = None,
    flight_id: str | None = None,
    status: SSRStatus | None = None,
    actor: Principal = require("ssr:read"),
):
    return ssr_service.list_ssrs(actor, booking_id, passenger_id, flight_id, status)


@router.get("/catalog", response_model=list[SSRCatalogItem], summary="SSR catalog",
            description="Every SSR type with price, options and constraints. Public.")
def catalog():
    return ssr_service.list_catalog()


@router.get("/available", response_model=list[SSRAvailability], responses=error_responses(400, 404, 409),
            summary="SSRs available to a passenger",
            description="For one passenger on one segment (default: the next segment that hasn't departed), shows every SSR type "
                        "with its eligibility (tier, passenger type, flight length, bassinet positions, duplicates) "
                        "and the tier-discounted price.")
def available(
    booking_id: str = Query(...),
    passenger_id: str = Query(...),
    flight_id: str | None = Query(None, description="Segment flight"),
    actor: Principal = require("ssr:read"),
):
    return ssr_service.available_ssrs(booking_id, passenger_id, flight_id, actor)


@router.post("", response_model=SSR, status_code=status.HTTP_201_CREATED, responses=error_responses(400, 404, 409),
             summary="Create an SSR",
             description="Requires `ssr:write` **and** the matching `ssr:<TYPE>` scope. At login these are granted "
                         "only for SSRs the user's tier allows, so an ineligible token cannot write. The backend also "
                         "re-checks the booking owner's current tier, passenger type (bassinet → infant), flight rules "
                         "(meal needs 90+ min, bassinet positions left), quantity and option.\n\n"
                         "Tier rules: Bronze — meal, wheelchair · Silver — + excess baggage · Gold — + lounge, bassinet.")
def create_ssr(payload: SSRCreate, actor: Principal = require("ssr:write")):
    return ssr_service.create_ssr(payload, actor)


@router.get("/{ssr_id}", response_model=SSR, responses=error_responses(404), summary="Get an SSR")
def get_ssr(ssr_id: str, actor: Principal = require("ssr:read")):
    return ssr_service.get_ssr(ssr_id, actor)


@router.delete("/{ssr_id}", response_model=SSR, responses=error_responses(404, 409), summary="Delete (cancel) an SSR",
               description="Marks the SSR CANCELLED. The record is kept for history.")
def delete_ssr(ssr_id: str, actor: Principal = require("ssr:write")):
    return ssr_service.cancel_ssr(ssr_id, actor)
