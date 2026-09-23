from fastapi import APIRouter, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional, require
from app.models.enums import CheckinStatus
from app.schemas.checkin import Checkin, CheckinCreate, CheckinLookup, CheckinResult, CheckinUpdate, CheckinValidation
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
             description="**Booking flow step 7a.** Finds the booking by **PNR + passenger last name** and returns, for "
                         "every flight segment, its live phase, its check-in window (opens 48 h, closes 4 h before "
                         "departure by default), and each passenger's eligibility. Open to guests.")
def validate_checkin(payload: CheckinLookup, _: Principal | None = optional("checkin:write")):
    return checkin_service.validate(payload.pnr, payload.last_name)


@router.post("", response_model=CheckinResult, status_code=status.HTTP_201_CREATED,
             responses=error_responses(400, 404, 409), summary="Create check-in",
             description="**Booking flow step 7b.** Checks in the selected passengers on the selected flights and issues "
                         "**one ticket / boarding pass per passenger per flight**. By default it covers every flight "
                         "whose window is open and every passenger not yet checked in. Passengers can check in one at a "
                         "time, but an adult with an infant on their lap must check in together with that infant. "
                         "Checking in twice returns 409.")
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
