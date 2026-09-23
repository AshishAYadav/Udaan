from fastapi import APIRouter

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.reference import AdminSummary
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/summary", response_model=AdminSummary, responses=error_responses(), summary="Dashboard summary (admin)",
            description="Record counts for the admin dashboard.")
def summary(_: Principal = require("admin")):
    return admin_service.summary()
