from fastapi import APIRouter

from app.api.common import error_responses
from app.schemas.reference import Airport
from app.services import reference_service

router = APIRouter(prefix="/airports", tags=["Airports"])


@router.get("", response_model=list[Airport], summary="List airports",
            description="All airports known to the sandbox, sorted by IATA code.")
def list_airports():
    return reference_service.list_airports()


@router.get("/{airport_id}", response_model=Airport, responses=error_responses(404, auth=False), summary="Get an airport",
            description="Airport by IATA code, e.g. DXB.")
def get_airport(airport_id: str):
    return reference_service.get_airport(airport_id)
