from fastapi import APIRouter, Query, Response, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional, require
from app.schemas.passenger import Passenger, PassengerCreate, PassengerUpdate
from app.services import passenger_service

router = APIRouter(prefix="/passengers", tags=["Passengers"])


@router.get("", response_model=list[Passenger], responses=error_responses(), summary="List passengers",
            description="Your passengers (admins: all passengers, optionally filtered by user).")
def list_passengers(
    user_id: str | None = Query(None, description="Admins only"),
    last_name: str | None = Query(None, description="Case-insensitive"),
    actor: Principal = require("bookings:read"),
):
    return passenger_service.list_passengers(actor, user_id, last_name)


@router.post("", response_model=Passenger, status_code=status.HTTP_201_CREATED, responses=error_responses(400, 404),
             summary="Add a passenger",
             description="**Booking flow step 2.** Open to guests. With a token, the passenger belongs to the caller "
                         "(admins may set `user_id`); without one, it is an unowned guest passenger. Passenger type comes from date of birth: under 2 = INFANT, under 12 = CHILD, "
                         "otherwise ADULT. If you supply `passenger_type`, it must match. Infants may name an "
                         "`accompanying_adult_id`.")
def create_passenger(payload: PassengerCreate, actor: Principal | None = optional("passengers:write")):
    return passenger_service.create_passenger(payload, actor)


@router.get("/{passenger_id}", response_model=Passenger, responses=error_responses(404), summary="Get a passenger")
def get_passenger(passenger_id: str, actor: Principal = require("bookings:read")):
    return passenger_service.get_passenger(passenger_id, actor)


@router.put("/{passenger_id}", response_model=Passenger, responses=error_responses(400, 404, 409),
            summary="Modify a passenger",
            description="Partial update. A date-of-birth change that alters the passenger type is rejected while the "
                        "passenger holds an active booking.")
def update_passenger(passenger_id: str, payload: PassengerUpdate, actor: Principal = require("passengers:write")):
    return passenger_service.update_passenger(passenger_id, payload, actor)


@router.delete("/{passenger_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(404, 409),
               summary="Delete a passenger", description="Passengers on an active booking cannot be deleted.")
def delete_passenger(passenger_id: str, actor: Principal = require("passengers:write")):
    passenger_service.delete_passenger(passenger_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
