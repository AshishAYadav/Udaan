"""Hosted checkout: pay a payment session with a card and confirm the held booking.

A successful payment triggers `payment.succeeded` and `booking.confirmed`; a decline triggers
`payment.failed` (the session stays open for retries until the hold expires).
"""
from urllib.parse import urlencode

from app.db.database import transaction
from app.db.database import repositories as db
from app.models.enums import BookingStatus
from app.services import booking_service, payment_service, webhook_service
from app.utils.errors import ConflictError, PaymentDeclinedError


def get_session(session_id: str) -> dict:
    booking_service.expire_holds()
    return payment_service.public_view(payment_service.get_by_session(session_id))


def _redirect(url: str | None, payment: dict, status: str) -> str | None:
    if not url:
        return None
    query = urlencode({"session_id": payment["session_id"], "pnr": payment["pnr"], "status": status})
    return f"{url}{'&' if '?' in url else '?'}{query}"


def pay(session_id: str, card) -> dict:
    booking_service.expire_holds()
    with transaction():
        payment = payment_service.get_by_session(session_id)
        booking = db.bookings.get(payment["booking_id"])
        if not booking or booking["status"] != BookingStatus.PENDING:
            raise ConflictError("This booking is no longer awaiting payment.")
        succeeded, reason, payment = payment_service.charge(payment, card)
        if succeeded:
            booking = booking_service.confirm_paid(payment)

    event_data = booking_service.event_data(booking, payment)
    if not succeeded:
        webhook_service.emit("payment.failed", {**event_data, "reason": reason})
        raise PaymentDeclinedError(reason)
    webhook_service.emit("payment.succeeded", event_data)
    webhook_service.emit("booking.confirmed", event_data)
    return {
        **payment_service.public_view(payment),
        "booking_id": booking["booking_id"],
        "redirect_url": _redirect(payment["success_url"], payment, "COMPLETED"),
    }
