"""Hosted payment sessions (checkout), modelled on Stripe Checkout.

A session is created for a held booking. It has a secret `session_id`, and its hosted page is
`{PUBLIC_UI_URL}/pay/{session_id}`, so anyone holding the link can pay. Card details are
checked against the sandbox test cards. Every attempt is logged, and only the card brand and
last four digits are stored.

Session status: PENDING → COMPLETED (→ REFUNDED) | EXPIRED | CANCELLED.
"""
import re
import secrets
from calendar import monthrange
from datetime import date, datetime

from app.auth.dependencies import Principal, owns
from app.config import settings
from app.db.database import next_id
from app.db.database import repositories as db
from app.models.enums import PaymentAttemptResult, PaymentStatus
from app.services import currency_service
from app.utils.errors import ConflictError, NotFoundError
from app.utils.timeutils import now_iso, parse_dt, utcnow

MERCHANT = "Udaan Airlines"

TEST_CARDS: dict[str, str] = {
    "378282246310005": "American Express",
    "371449635398431": "American Express",
    "378734493671000": "American Express Corporate",
    "5610591081018250": "Australian BankCard",
    "30569309025904": "Diners Club",
    "38520000023237": "Diners Club",
    "6011111111111117": "Discover",
    "6011000990139424": "Discover",
    "3530111333300000": "JCB",
    "3566002020360505": "JCB",
    "5555555555554444": "MasterCard",
    "5105105105105100": "MasterCard",
    "4111111111111111": "Visa",
    "4012888888881881": "Visa",
    "4222222222222": "Visa",
    "76009244561": "Dankort (PBS)",
    "5019717010103742": "Dankort (PBS)",
    "6331101999990016": "Switch/Solo (Paymentech)",
}


def payment_url(session_id: str) -> str:
    return f"{settings.public_ui_url}/pay/{session_id}"


def _expired(payment: dict) -> bool:
    return payment["status"] == PaymentStatus.PENDING and utcnow() >= parse_dt(payment["expires_at"])


def create_session(booking: dict, currency: str, expires_at: datetime, breakdown: list[dict], options: dict) -> dict:
    """Open a new session for a booking; any other open session for it is cancelled."""
    for old in db.payments.find(booking_id=booking["booking_id"], status=PaymentStatus.PENDING.value):
        db.payments.update(old["payment_id"], {"status": PaymentStatus.CANCELLED.value, "updated_at": now_iso()})
    currency = currency_service.validate(currency)
    session_id = "ps_" + secrets.token_urlsafe(24)
    payment = {
        "payment_id": next_id("PAY"),
        "session_id": session_id,
        "booking_id": booking["booking_id"],
        "pnr": booking["pnr"],
        "user_id": booking["user_id"],
        "amount": currency_service.convert(booking["base_amount"], currency),
        "currency": currency,
        "base_amount": booking["base_amount"],
        "base_currency": settings.currency,
        "exchange_rate": currency_service.RATES[currency],
        "breakdown": breakdown,
        "status": PaymentStatus.PENDING.value,
        "payment_url": payment_url(session_id),
        "expires_at": expires_at.isoformat(timespec="seconds"),
        "client_reference_id": options.get("client_reference_id"),
        "metadata": options.get("metadata") or {},
        "success_url": options.get("success_url"),
        "cancel_url": options.get("cancel_url"),
        "card": None,
        "created_at": now_iso(),
        "completed_at": None,
        "updated_at": None,
    }
    return db.payments.insert(payment)


def get_by_session(session_id: str) -> dict:
    payment = db.payments.find_one(session_id=session_id)
    if not payment:
        raise NotFoundError("Payment session not found.")
    if _expired(payment):
        payment = db.payments.update(payment["payment_id"], {"status": PaymentStatus.EXPIRED.value, "updated_at": now_iso()})
    return payment


def get_payment(payment_id: str, actor: Principal | None) -> dict:
    payment = db.payments.get(payment_id)
    if not payment or not owns(actor, payment["user_id"]):
        raise NotFoundError(f"Payment {payment_id} not found.")
    return payment


def list_payments(actor: Principal, booking_id: str | None = None) -> list[dict]:
    def matches(p: dict) -> bool:
        return (actor.is_admin or p["user_id"] == actor.user_id) and (not booking_id or p["booking_id"] == booking_id)

    return sorted(db.payments.filter(matches), key=lambda p: p["payment_id"], reverse=True)


def attempts(payment_id: str) -> list[dict]:
    return sorted(db.payment_attempts.find(payment_id=payment_id), key=lambda a: a["attempt_id"])


# Card checks

def _card_error(number: str, expiry: str, cvv: str, holder: str) -> tuple[str | None, str | None]:
    """Return (brand, decline reason). The reason is None when the card is accepted."""
    brand = TEST_CARDS.get(number)
    if not brand:
        return None, "Card declined: sandbox accepts only the published test card numbers."
    match = re.fullmatch(r"(\d{2})/?(\d{2})", expiry.strip())
    if not match or not 1 <= int(match.group(1)) <= 12:
        return brand, "Invalid expiry date; use MMYY."
    year, month = 2000 + int(match.group(2)), int(match.group(1))
    if date(year, month, monthrange(year, month)[1]) < date.today():
        return brand, "Card declined: the card has expired."
    expected_cvv = 4 if brand.startswith("American Express") else 3
    if not re.fullmatch(rf"\d{{{expected_cvv}}}", cvv.strip()):
        return brand, f"Invalid security code; {brand} uses {expected_cvv} digits."
    if not holder.strip():
        return brand, "Cardholder name is required."
    return brand, None


def charge(payment: dict, card) -> tuple[bool, str | None, dict]:
    """Validate the card and record the attempt. Returns (succeeded, decline reason, updated payment)."""
    if payment["status"] != PaymentStatus.PENDING:
        raise ConflictError(f"This payment session is {payment['status'].lower()}.")
    number = re.sub(r"[\s-]", "", card.card_number)
    brand, reason = _card_error(number, card.expiry, card.cvv, card.holder_name)
    card_info = {"brand": brand or "Unknown", "last4": number[-4:], "holder_name": card.holder_name.strip()}
    db.payment_attempts.insert(
        {
            "attempt_id": next_id("ATT"),
            "payment_id": payment["payment_id"],
            "result": (PaymentAttemptResult.DECLINED if reason else PaymentAttemptResult.SUCCEEDED).value,
            "reason": reason,
            "card": card_info,
            "created_at": now_iso(),
        }
    )
    if reason:
        return False, reason, payment
    updated = db.payments.update(
        payment["payment_id"],
        {"status": PaymentStatus.COMPLETED.value, "card": card_info, "completed_at": now_iso(), "updated_at": now_iso()},
    )
    return True, None, updated


def close_open_sessions(booking_id: str, status: PaymentStatus) -> None:
    for payment in db.payments.find(booking_id=booking_id, status=PaymentStatus.PENDING.value):
        db.payments.update(payment["payment_id"], {"status": status.value, "updated_at": now_iso()})


def refund(payment_id: str | None) -> None:
    payment = db.payments.get(payment_id) if payment_id else None
    if payment and payment["status"] == PaymentStatus.COMPLETED:
        db.payments.update(payment_id, {"status": PaymentStatus.REFUNDED.value, "updated_at": now_iso()})


def public_view(payment: dict) -> dict:
    """What the hosted page may show: no personal data beyond the booking summary."""
    booking = db.bookings.get(payment["booking_id"]) or {}
    flights = [db.flights.get(s["flight_id"]) for s in booking.get("segments", [])]
    return {
        "session_id": payment["session_id"],
        "status": payment["status"],
        "merchant": MERCHANT,
        "description": f"Flight booking {payment['pnr']}",
        "pnr": payment["pnr"],
        "amount": payment["amount"],
        "currency": payment["currency"],
        "base_amount": payment["base_amount"],
        "base_currency": payment["base_currency"],
        "expires_at": payment["expires_at"],
        "passengers": len(booking.get("passenger_ids", [])),
        "itinerary": [
            f"{f['flight_number']} {f['departure_airport']}→{f['arrival_airport']} {f['departure_time'][:16].replace('T', ' ')}"
            for f in flights if f
        ],
        "card": payment["card"],
        "success_url": payment["success_url"],
        "cancel_url": payment["cancel_url"],
    }
