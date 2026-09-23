from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.models.enums import SSRType
from app.schemas.fare import Fare, SSRFareQuote
from app.services import fare_service, reference_service

router = APIRouter(prefix="/fares", tags=["Fares"])


@router.get("/flight/{flight_id}", response_model=list[Fare], responses=error_responses(404, auth=False),
            summary="Get fares for a flight",
            description="One fare per cabin with adult base price and seat inventory. "
                        "Child fares are 75% and infant fares 10% of the adult fare.")
def fares_for_flight(flight_id: str):
    return fare_service.fares_for_flight(flight_id)


@router.get("/ssr/{ssr_type}", response_model=SSRFareQuote, responses=error_responses(404, auth=False),
            summary="Get fare for an SSR",
            description="Price of a special service request. Supply `tier_id` to apply that tier's discounts "
                        "and see eligibility.")
def fare_for_ssr(
    ssr_type: SSRType,
    quantity: int = Query(1, ge=1, le=10),
    tier_id: str | None = Query(None, description="Price for this tier, e.g. GOLD"),
):
    tier = reference_service.get_tier(tier_id) if tier_id else None
    return fare_service.ssr_price(ssr_type, quantity, tier)
