from fastapi import APIRouter, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional, require
from app.models.enums import CheckinStatus
from app.schemas.checkin import (
    Checkin,
    CheckinCreate,
    CheckinResult,
    CheckinUpdate,
    CheckinValidateRequest,
    CheckinValidation,
)
from app.services import checkin_service

router = APIRouter(prefix="/checkins", tags=["Check-in"])


@router.get("", response_model=list[Checkin], responses=error_responses(), summary="List check-ins (admin)",
            description="Check-in records filtered by booking, PNR, flight or status.")
def list_checkins(
    booking_id: str | None = None,
    pnr: str | None = None,
    flight_id: str | None = None,
    status: CheckinStatus | None = None,
    _: Principal = require("admin"),
):
    return checkin_service.list_checkins(booking_id, pnr, flight_id, status)


@router.post("/validate", response_model=CheckinValidation, responses=error_responses(404),
             summary="Validate check-in",
             description="**Booking flow step 8a.** Finds the booking by **PNR + passenger last name** and picks the "
                         "journey to check in (default: the next upcoming journey). It returns the segments covered "
                         "and which passengers can check in: the booking must be active, the check-in window open, "
                         "no flight cancelled, and the passenger not already checked in.")
def validate_checkin(payload: CheckinValidateRequest, _: Principal | None = optional("checkin:write")):
    return checkin_service.validate(payload.pnr, payload.last_name, payload.direction)


@router.post("", response_model=CheckinResult, status_code=status.HTTP_201_CREATED,
             responses=error_responses(400, 404, 409), summary="Create check-in",
             description="**Booking flow step 8b.** Through check-in: checks the selected (default: all eligible) "
                         "passengers in on **every remaining segment** of the journey, assigns seats (infants get "
                         "`INF`) and **issues one ticket / boarding pass per passenger per segment**. Checking in a "
                         "passenger twice returns 409.")
def create_checkin(payload: CheckinCreate, _: Principal | None = optional("checkin:write")):
    return checkin_service.check_in(payload)


@router.get("/{checkin_id}", response_model=Checkin, responses=error_responses(404), summary="Get a check-in",
            description="Booking owner or admin.")
def get_checkin(checkin_id: str, actor: Principal = require("bookings:read")):
    return checkin_service.get_checkin(checkin_id, actor)


@router.put("/{checkin_id}", response_model=Checkin, responses=error_responses(400, 404, 409),
            summary="Update check-in",
            description="Change seat (must be free and in the booked cabin) or set status NOT_CHECKED_IN to offload "
                        "the passenger, which cancels their ticket. Booking owner or admin.")
def update_checkin(checkin_id: str, payload: CheckinUpdate, actor: Principal = require("checkin:write")):
    return checkin_service.update_checkin(checkin_id, payload, actor)
