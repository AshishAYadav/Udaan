from datetime import date

from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.models.enums import CabinClass
from app.schemas.itinerary import TripSearchResult
from app.services import itinerary_service

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])


@router.get("/search", response_model=TripSearchResult, response_model_by_alias=True,
            responses=error_responses(400, 404, auth=False), summary="Search one-way or round-trip itineraries",
            description="**Booking flow step 1.** Direct and one-stop itineraries for the outbound date and, if "
                        "`return_date` is given, for the return date.\n\n"
                        "A connection is offered only when the layover is at least the minimum connecting time "
                        "(60 min domestic / 90 min international) and no longer than the maximum connection time "
                        "(4 h domestic / 24 h international). A longer layover counts as a stopover. Each cabin shows the adult, child "
                        "and infant fare summed over all segments, plus the total for the party. Only cabins available on "
                        "every segment, with enough seats for the adults and children, are offered. Pass an itinerary's `flight_ids` as "
                        "`outbound_flight_ids` / `return_flight_ids` when paying and booking.")
def search(
    origin: str = Query(..., min_length=3, max_length=3, examples=["DEL"]),
    destination: str = Query(..., min_length=3, max_length=3, examples=["LHR"]),
    date: date = Query(..., description="Outbound local departure date"),
    return_date: date | None = Query(None, description="Return local departure date (round trip)"),
    cabin_class: CabinClass | None = None,
    adults: int = Query(1, ge=1, le=9, description="Passengers aged 12+"),
    children: int = Query(0, ge=0, le=8, description="Passengers aged 2-11 (75% fare, own seat)"),
    infants: int = Query(0, ge=0, le=9, description="Passengers under 2 (10% fare, on an adult's lap)"),
):
    return itinerary_service.search_trip(origin, destination, date, return_date, cabin_class, adults, children, infants)
