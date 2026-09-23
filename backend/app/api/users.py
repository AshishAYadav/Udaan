from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.reference import UserDetail
from app.services import reference_service
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserDetail], responses=error_responses(), summary="List users (admin)",
            description="All users with their membership tier. Requires the `admin` scope.")
def list_users(tier_id: str | None = Query(None, description="Filter by tier, e.g. GOLD"), _: Principal = require("admin")):
    return reference_service.list_users(tier_id)


@router.get("/{user_id}", response_model=UserDetail, responses=error_responses(404), summary="Get a user",
            description="A user with membership tier. Customers can only read themselves.")
def get_user(user_id: str, actor: Principal = require("profile")):
    if not actor.owns(user_id):
        raise NotFoundError(f"User {user_id} not found.")
    return reference_service.get_user(user_id)
