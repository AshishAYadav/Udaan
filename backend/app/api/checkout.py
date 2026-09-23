from fastapi import APIRouter

from app.api.common import error_responses
from app.schemas.common import ErrorResponse
from app.schemas.payment import CardDetails, PaymentResult, PaymentSessionPublic
from app.services import checkout_service

router = APIRouter(prefix="/payment-sessions", tags=["Checkout (hosted payment page)"])


@router.get("/{session_id}", response_model=PaymentSessionPublic, responses=error_responses(404, auth=False),
            summary="Get a payment session",
            description="Public data for the hosted payment page `/pay/{session_id}`: merchant, amount, currency, "
                        "PNR, itinerary summary, status and expiry. The session id is the secret; no login is needed.")
def get_session(session_id: str):
    return checkout_service.get_session(session_id)


@router.post("/{session_id}/pay", response_model=PaymentResult,
             responses={**error_responses(404, 409, auth=False), 402: {"model": ErrorResponse, "description": "Card declined"}},
             summary="Pay a payment session",
             description="Charges a sandbox test card. Only the published test card numbers are accepted, with a "
                         "future MMYY expiry and a CVV (4 digits for American Express, otherwise 3).\n\n"
                         "On success the session becomes COMPLETED, the booking CONFIRMED, and webhooks "
                         "`payment.succeeded` and `booking.confirmed` are sent. A decline returns **402**, sends "
                         "`payment.failed`, and leaves the session open for another attempt until it expires.")
def pay(session_id: str, card: CardDetails):
    return checkout_service.pay(session_id, card)
