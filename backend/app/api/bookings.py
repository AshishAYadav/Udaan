from fastapi import APIRouter, Query, Response, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional, require
from app.models.enums import BookingStatus
from app.schemas.booking import (
    Booking,
    BookingCancelRequest,
    BookingChangeRequest,
    BookingChangeResult,
    BookingCreate,
    BookingHistoryEntry,
    BookingUpdate,
    BookingView,
)
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])

LAST_NAME = Query(..., min_length=1, description="Last name of any passenger on the booking (case-insensitive)")
MANAGE_LAST_NAME = Query(None, description="Required unless you are logged in as the owner or an admin")


@router.get("", response_model=list[Booking], responses=error_responses(), summary="List bookings",
            description="The caller's bookings, newest first. Admins see every booking, including guest bookings, and "
                        "may filter by `user_id`.")
def list_bookings(
    user_id: str | None = Query(None, description="Admins only"),
    status: BookingStatus | None = None,
    pnr: str | None = None,
    actor: Principal = require("bookings:read"),
):
    return booking_service.list_bookings(actor, user_id, status, pnr)


@router.post("", response_model=BookingView, status_code=status.HTTP_201_CREATED,
             responses=error_responses(400, 404, 409), summary="Make a booking",
             description="**Booking flow step 6.** Confirms a one-way or round-trip booking (each journey can have one "
                         "connection) and generates a unique 6-character PNR.\n\n"
                         "Requires bookable flights with valid connections, the cabin on every segment with enough "
                         "seats, at least one adult (infants ≤ adults), and a **COMPLETED** payment created for exactly "
                         "these flights, cabin and passengers. Seats are taken on every segment. Tickets are issued at check-in, not here.\n\n"
                         "Open to **guests**: send no token and include `payment_key`. Guest bookings cannot add "
                         "tier-based special services.")
def create_booking(payload: BookingCreate, actor: Principal | None = optional("bookings:write")):
    return booking_service.create_booking(payload, actor)


@router.get("/pnr/{pnr}", response_model=BookingView, responses=error_responses(404), summary="Retrieve booking by PNR + last name",
            description="**Booking flow step 7.** Airline convention: a PNR is only disclosed together with the last "
                        "name of a passenger on it. Open to guests.")
def get_by_pnr(pnr: str, last_name: str = LAST_NAME, _: Principal | None = optional("bookings:read")):
    return booking_service.build_view(booking_service.find_by_pnr(pnr, last_name))


@router.get("/{booking_id}", response_model=BookingView, responses=error_responses(404),
            summary="Retrieve booking by booking ID + last name",
            description="Booking owners and admins can omit `last_name`. Anyone else needs the last name of a "
                        "passenger on the booking.")
def get_booking(
    booking_id: str,
    last_name: str | None = MANAGE_LAST_NAME,
    actor: Principal | None = optional("bookings:read"),
):
    return booking_service.build_view(booking_service.get_booking(booking_id, actor, last_name))


@router.put("/{booking_id}", response_model=BookingView, responses=error_responses(400, 404, 409),
            summary="Update booking contact details", description="Owner, admin, or anyone with a passenger's `last_name`.")
def update_booking(
    booking_id: str, payload: BookingUpdate, last_name: str | None = MANAGE_LAST_NAME,
    actor: Principal | None = optional("bookings:write"),
):
    return booking_service.update_booking(booking_id, payload, actor, last_name)


@router.post("/{booking_id}/change", response_model=BookingChangeResult, responses=error_responses(400, 404, 409),
             summary="Change a journey",
             description="Replaces the OUTBOUND or RETURN journey with another direct or connecting itinerary between "
                         "the same airports and in the same cabin. Allowed for the owner, an admin, or anyone (including guests) "
                         "with a passenger's `last_name`.\n\n"
                         "- Allowed only more than **24 hours** before the journey's first departure.\n"
                         "- The new journey must depart no later than **7 days** after the original.\n"
                         "- Connections and the order of the trip must stay valid, there must be enough seats, and nobody can be checked in.\n\n"
                         "Seats move with the journey. SSRs on flights that were removed are cancelled. The status "
                         "becomes CHANGED.")
def change_booking(
    booking_id: str, payload: BookingChangeRequest, last_name: str | None = MANAGE_LAST_NAME,
    actor: Principal | None = optional("bookings:write"),
):
    return booking_service.change_journey(booking_id, payload.direction, payload.new_flight_ids, actor, last_name)


@router.post("/{booking_id}/cancel", response_model=BookingView, responses=error_responses(400, 404, 409),
             summary="Cancel a booking",
             description="Cancels before the first departure: status CANCELLED, seats released on all segments, "
                         "payment REFUNDED, SSRs, check-ins and tickets cancelled. The PNR is kept. Owner, admin, or "
                         "anyone with a passenger's `last_name`.")
def cancel_booking(
    booking_id: str, payload: BookingCancelRequest | None = None, last_name: str | None = MANAGE_LAST_NAME,
    actor: Principal | None = optional("bookings:write"),
):
    return booking_service.cancel_booking(booking_id, actor, payload.reason if payload else None, last_name)


@router.get("/{booking_id}/history", response_model=list[BookingHistoryEntry], responses=error_responses(404),
            summary="Booking history", description="Audit trail. Owner, admin, or with a passenger's `last_name`.")
def booking_history(
    booking_id: str, last_name: str | None = MANAGE_LAST_NAME, actor: Principal | None = optional("bookings:read")
):
    return booking_service.history(booking_id, actor, last_name)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(404),
               summary="Delete a booking (admin)",
               description="Permanently removes the booking with its check-ins, tickets, SSRs and history. An active "
                           "booking's seats are released and its payment refunded first. Requires `admin`.")
def delete_booking(booking_id: str, _: Principal = require("admin")):
    booking_service.delete_booking(booking_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
