"""Outbound webhooks (event notifications), signed like Stripe's.

Subscribers register an HTTPS endpoint and receive JSON events:
    {"id": "evt_…", "type": "payment.succeeded", "created": "...", "data": {...}}
Each request carries `Udaan-Signature: t=<unix>,v1=<hex HMAC-SHA256(secret, "<t>.<body>")>`.
Deliveries run in a background thread and are logged with the HTTP result.
"""
import hashlib
import hmac
import json
import secrets
import threading
import time
import urllib.error
import urllib.request

from app.config import settings
from app.db.database import next_id
from app.db.database import repositories as db
from app.utils.errors import BadRequestError, NotFoundError
from app.utils.timeutils import now_iso

EVENT_TYPES = [
    "booking.held",
    "booking.confirmed",
    "booking.expired",
    "booking.cancelled",
    "payment.succeeded",
    "payment.failed",
]


def list_subscriptions() -> list[dict]:
    return db.webhooks.all()


def create_subscription(url: str, events: list[str], description: str | None) -> dict:
    if not url.startswith(("http://", "https://")):
        raise BadRequestError("Webhook URL must start with http:// or https://.")
    unknown = set(events) - set(EVENT_TYPES) - {"*"}
    if unknown:
        raise BadRequestError(f"Unknown event type(s): {', '.join(sorted(unknown))}.")
    subscription = {
        "webhook_id": next_id("WH"),
        "url": url,
        "events": events or ["*"],
        "description": description,
        "secret": "whsec_" + secrets.token_urlsafe(24),
        "active": True,
        "created_at": now_iso(),
    }
    return db.webhooks.insert(subscription)


def delete_subscription(webhook_id: str) -> None:
    if not db.webhooks.get(webhook_id):
        raise NotFoundError(f"Webhook {webhook_id} not found.")
    db.webhooks.remove(webhook_id)


def list_deliveries(limit: int = 100) -> list[dict]:
    return sorted(db.webhook_deliveries.all(), key=lambda d: d["delivery_id"], reverse=True)[:limit]


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _deliver(subscription: dict, event: dict) -> None:
    body = json.dumps(event, default=str).encode()
    timestamp = int(time.time())
    request = urllib.request.Request(
        subscription["url"],
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Udaan-Signature": sign(subscription["secret"], timestamp, body)},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.webhook_timeout_seconds) as response:
            status, error = response.status, None
    except urllib.error.HTTPError as exc:
        status, error = exc.code, str(exc)
    except Exception as exc:  # network errors are recorded, never raised
        status, error = None, str(exc)
    db.webhook_deliveries.insert(
        {
            "delivery_id": next_id("WHD"),
            "webhook_id": subscription["webhook_id"],
            "event_id": event["id"],
            "event_type": event["type"],
            "url": subscription["url"],
            "status_code": status,
            "success": status is not None and 200 <= status < 300,
            "error": error,
            "delivered_at": now_iso(),
        }
    )


def emit(event_type: str, data: dict) -> dict:
    """Send an event to every matching active subscription (asynchronously)."""
    event = {"id": "evt_" + secrets.token_hex(12), "type": event_type, "created": now_iso(), "data": data}
    for subscription in db.webhooks.find(active=True):
        if "*" in subscription["events"] or event_type in subscription["events"]:
            threading.Thread(target=_deliver, args=(subscription, event), daemon=True).start()
    return event
