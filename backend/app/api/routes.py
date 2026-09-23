from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.schemas.reference import Airport, Route, RouteDetail
from app.services import reference_service

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("", response_model=list[Route], summary="List routes",
            description="All routes, optionally filtered by active flag.")
def list_routes(active: bool | None = Query(None, description="Filter by active flag")):
    return reference_service.list_routes(active)


@router.get("/valid", response_model=list[RouteDetail], summary="Get valid flight routes",
            description="Active routes whose origin and destination airports both exist, with airport details. "
                        "Optionally filter by origin and/or destination.")
def valid_routes(origin: str | None = None, destination: str | None = None):
    return reference_service.valid_routes(origin, destination)


@router.get("/sources", response_model=list[Airport], summary="Get source airports",
            description="Airports that are the origin of at least one valid route.")
def source_airports():
    return reference_service.source_airports()


@router.get("/destinations", response_model=list[Airport], responses=error_responses(404, auth=False),
            summary="Get destination airports",
            description="Airports reachable on a valid route. Pass `origin` to restrict to destinations served from it.")
def destination_airports(origin: str | None = Query(None, description="Origin IATA code, e.g. DXB")):
    return reference_service.destination_airports(origin)


@router.get("/{route_id}", response_model=Route, responses=error_responses(404, auth=False), summary="Get a route")
def get_route(route_id: str):
    return reference_service.get_route(route_id)
