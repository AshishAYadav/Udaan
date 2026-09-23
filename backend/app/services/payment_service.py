"""Mock payment gateway.

State machine:
    PENDING --APPROVE--> APPROVED --complete--> COMPLETED --(booking cancelled)--> REFUNDED
    PENDING --REJECT---> REJECTED --complete--> FAILED

Guests (no token) are identified by the payment's `access_key`, returned once when
the payment is created and presented as the `X-Payment-Key` header afterwards.
"""
import hmac
import secrets

from app.auth.dependencies import Principal, owns
from app.db.database import next_id
from app.db.database import repositories as db
from app.models.enums import PaymentAction, PaymentStatus
from app.services import itinerary_service
from app.services import reference_service as ref
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError
from app.utils.timeutils import now_iso


def resolve_user_id(requested: str | None, actor: Principal | None) -> str | None:
    """Guests book without an account; customers act for themselves; admins may act for any user."""
    if actor is None:
        if requested:
            raise ForbiddenError("Log in to pay or book on behalf of a user account.")
        return None
    if actor.is_admin:
        user_id = requested or actor.user_id
    elif requested and requested != actor.user_id:
        raise ForbiddenError("You can only make payments and bookings for your own account.")
    else:
        user_id = actor.user_id
    ref.get_user(user_id)
    return user_id


def get_payment(payment_id: str, actor: Principal | None, access_key: str | None = None) -> dict:
    """Owner/admin by token, or anyone presenting the payment's access key."""
    payment = db.payments.get(payment_id)
    if not payment:
        raise NotFoundError(f"Payment {payment_id} not found.")
    key_ok = bool(access_key) and hmac.compare_digest(access_key, payment.get("access_key", ""))
    if not (owns(actor, payment["user_id"]) or key_ok):
        raise NotFoundError(f"Payment {payment_id} not found.")
    return payment


def create_payment(data, actor: Principal | None) -> dict:
    """Create a PENDING payment whose amount is calculated by the server."""
    user_id = resolve_user_id(data.user_id, actor)
    trip = itinerary_service.prepare_trip(data.outbound_flight_ids, data.return_flight_ids, data.class_id, data.passenger_ids)
    itinerary_service.ensure_passengers_belong_to(trip["party"], user_id)

    payment = {
        "payment_id": next_id("PAY"),
        "user_id": user_id,
        "outbound_flight_ids": data.outbound_flight_ids,
        "return_flight_ids": data.return_flight_ids,
        "class_id": data.class_id.value,
        "passenger_ids": data.passenger_ids,
        "amount": trip["quote"]["total"],
        "currency": trip["quote"]["currency"],
        "method": data.method,
        "status": PaymentStatus.PENDING.value,
        "breakdown": trip["quote"]["lines"],
        "booking_id": None,
        "access_key": secrets.token_urlsafe(16),
        "created_at": now_iso(),
        "updated_at": None,
    }
    return db.payments.insert(payment)


def apply_action(payment_id: str, action: PaymentAction, actor: Principal | None, access_key: str | None = None) -> dict:
    payment = get_payment(payment_id, actor, access_key)
    if payment["status"] != PaymentStatus.PENDING:
        raise ConflictError(f"Payment {payment_id} is {payment['status']}; only PENDING payments can be approved or rejected.")
    status = PaymentStatus.APPROVED if action == PaymentAction.APPROVE else PaymentStatus.REJECTED
    return db.payments.update(payment_id, {"status": status.value, "updated_at": now_iso()})


def complete_payment(payment_id: str, actor: Principal | None, access_key: str | None = None) -> dict:
    payment = get_payment(payment_id, actor, access_key)
    transitions = {PaymentStatus.APPROVED: PaymentStatus.COMPLETED, PaymentStatus.REJECTED: PaymentStatus.FAILED}
    status = PaymentStatus(payment["status"])
    if status == PaymentStatus.PENDING:
        raise ConflictError(f"Payment {payment_id} must be approved or rejected before completion.")
    if status not in transitions:
        raise ConflictError(f"Payment {payment_id} is already finalised ({status}).")
    return db.payments.update(payment_id, {"status": transitions[status].value, "updated_at": now_iso()})


def payment_status(payment_id: str, actor: Principal | None, access_key: str | None = None) -> dict:
    payment = get_payment(payment_id, actor, access_key)
    return {
        "payment_id": payment_id,
        "status": payment["status"],
        "amount": payment["amount"],
        "currency": payment["currency"],
        "booking_id": payment["booking_id"],
        "can_create_booking": payment["status"] == PaymentStatus.COMPLETED and not payment["booking_id"],
    }


def refund(payment_id: str) -> None:
    payment = db.payments.get(payment_id)
    if payment and payment["status"] == PaymentStatus.COMPLETED:
        db.payments.update(payment_id, {"status": PaymentStatus.REFUNDED.value, "updated_at": now_iso()})
