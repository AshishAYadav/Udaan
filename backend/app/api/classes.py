from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.schemas.reference import AvailableCabinClass, CabinClassInfo
from app.services import fare_service, reference_service

router = APIRouter(prefix="/classes", tags=["Cabin classes"])


@router.get("", response_model=list[CabinClassInfo], summary="List cabin classes",
            description="Economy, Premium Economy, Business and First.")
def list_classes():
    return reference_service.list_classes()


@router.get("/available", response_model=list[AvailableCabinClass], responses=error_responses(404, auth=False),
            summary="Get available cabin classes for a flight",
            description="Cabins offered on the flight that still have at least `passengers` seats, with adult fare.")
def available_classes(
    flight_id: str = Query(..., description="Flight ID, e.g. FLT001"),
    passengers: int = Query(1, ge=1, le=9, description="Seats required"),
):
    classes = {c["class_id"]: c for c in reference_service.list_classes()}
    return [
        {
            **classes[f["class_id"]],
            "fare_id": f["fare_id"],
            "price": f["base_price"],
            "currency": f["currency"],
            "available_seats": f["available_seats"],
        }
        for f in fare_service.fares_for_flight(flight_id)
        if f["available_seats"] >= passengers
    ]
