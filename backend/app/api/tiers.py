from fastapi import APIRouter

from app.api.common import error_responses
from app.schemas.reference import Tier
from app.services import reference_service

router = APIRouter(prefix="/tiers", tags=["Tiers"])


@router.get("", response_model=list[Tier], summary="List membership tiers",
            description="Tier levels with eligible SSRs, free SSRs, discounts and benefits, ordered by priority.")
def list_tiers():
    return reference_service.list_tiers()


@router.get("/{tier_id}", response_model=Tier, responses=error_responses(404, auth=False), summary="Get a tier",
            description="Details of one tier level (BRONZE, SILVER or GOLD).")
def get_tier(tier_id: str):
    return reference_service.get_tier(tier_id)
