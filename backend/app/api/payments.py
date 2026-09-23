from fastapi import APIRouter, Header, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional
from app.schemas.payment import Payment, PaymentCreate, PaymentStatusResponse, PaymentUpdate
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])

GUEST_KEY = Header(None, alias="X-Payment-Key", description="Guests: the access_key returned when the payment was created")


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED, responses=error_responses(400, 404, 409),
             summary="Create a payment",
             description="**Booking flow step 3.** Creates a PENDING mock payment for a trip (outbound and optional "
                         "return flights), cabin and passengers. The server validates connections and seats and "
                         "calculates the amount: each passenger pays on every segment. Passengers must belong to the "
                         "paying user, or be new guest passengers. No card data is accepted or stored.\n\n"
                         "**Guests** (no token) must keep the returned `access_key`. They send it as the `X-Payment-Key` "
                         "header on the payment endpoints, and as `payment_key` when booking.")
def create_payment(payload: PaymentCreate, actor: Principal | None = optional("payments:write")):
    return payment_service.create_payment(payload, actor)


@router.put("/{payment_id}", response_model=Payment, responses=error_responses(404, 409),
            summary="Update payment (approve / reject)",
            description="**Booking flow step 4.** Mock gateway decision for a PENDING payment: "
                        "`APPROVE` → APPROVED, `REJECT` → REJECTED.")
def update_payment(
    payment_id: str, payload: PaymentUpdate, key: str | None = GUEST_KEY, actor: Principal | None = optional("payments:write")
):
    return payment_service.apply_action(payment_id, payload.action, actor, key)


@router.post("/{payment_id}/complete", response_model=Payment, responses=error_responses(404, 409),
             summary="Complete a payment",
             description="**Booking flow step 5.** Finalises the payment: APPROVED → COMPLETED, REJECTED → FAILED. "
                         "Only a COMPLETED payment can confirm a booking.")
def complete_payment(payment_id: str, key: str | None = GUEST_KEY, actor: Principal | None = optional("payments:write")):
    return payment_service.complete_payment(payment_id, actor, key)


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse, responses=error_responses(404),
            summary="Get payment status")
def payment_status(payment_id: str, key: str | None = GUEST_KEY, actor: Principal | None = optional("bookings:read")):
    return payment_service.payment_status(payment_id, actor, key)


@router.get("/{payment_id}", response_model=Payment, responses=error_responses(404), summary="Get a payment")
def get_payment(payment_id: str, key: str | None = GUEST_KEY, actor: Principal | None = optional("bookings:read")):
    return payment_service.get_payment(payment_id, actor, key)
