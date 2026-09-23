from fastapi import APIRouter, Query

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.payment import Payment, PaymentAttempt
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=list[Payment], responses=error_responses(), summary="List payments",
            description="Payment sessions for your bookings (admins: all), newest first.")
def list_payments(booking_id: str | None = Query(None), actor: Principal = require("bookings:read")):
    return payment_service.list_payments(actor, booking_id)


@router.get("/{payment_id}", response_model=Payment, responses=error_responses(404), summary="Get a payment",
            description="A payment session with its status, amount, currency and (after payment) card brand and last 4 digits.")
def get_payment(payment_id: str, actor: Principal = require("bookings:read")):
    return payment_service.get_payment(payment_id, actor)


@router.get("/{payment_id}/attempts", response_model=list[PaymentAttempt], responses=error_responses(404),
            summary="Payment attempts", description="Every card attempt on the session, with the decline reason if any.")
def payment_attempts(payment_id: str, actor: Principal = require("bookings:read")):
    payment_service.get_payment(payment_id, actor)
    return payment_service.attempts(payment_id)
