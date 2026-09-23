from datetime import timedelta

from fastapi import APIRouter, Query, Response, status

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.misc import ScheduleGenerateRequest, ScheduleGenerateResult, Webhook, WebhookCreate, WebhookDelivery
from app.schemas.reference import AdminSummary
from app.services import admin_service, booking_service, schedule_generator, webhook_service
from app.utils.timeutils import utcnow

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/summary", response_model=AdminSummary, responses=error_responses(), summary="Dashboard summary (admin)",
            description="Record counts for the admin dashboard.")
def summary(_: Principal = require("admin")):
    return admin_service.summary()


@router.post("/schedules/generate", response_model=ScheduleGenerateResult, responses=error_responses(400),
             summary="Generate flight schedules (admin)",
             description="Creates 3–4 flights per route per day (morning / afternoon / night) for the date range. Each "
                         "flight is validated: active route, future departure, unique flight number per day, and an "
                         "aircraft free for departure → arrival + ground time. Long-haul routes use wide-bodies. "
                         "Slots that can't be filled are skipped and counted. Requires `flights:write`.")
def generate_schedules(payload: ScheduleGenerateRequest, _: Principal = require("flights:write")):
    start = payload.start_date or utcnow().date() + timedelta(days=1)
    return schedule_generator.generate(
        start, payload.days, payload.min_per_route, payload.max_per_route, payload.seed, payload.route_ids
    )


@router.post("/holds/expire", summary="Expire unpaid holds now (admin)",
             description="Releases seats of unpaid bookings past their hold expiry. This also runs automatically every minute.")
def expire_holds(_: Principal = require("admin")):
    return {"expired": booking_service.expire_holds()}


@router.get("/webhooks", response_model=list[Webhook], responses=error_responses(), summary="List webhook subscriptions (admin)")
def list_webhooks(_: Principal = require("admin")):
    return webhook_service.list_subscriptions()


@router.post("/webhooks", response_model=Webhook, status_code=status.HTTP_201_CREATED, responses=error_responses(400),
             summary="Subscribe a webhook endpoint (admin)",
             description="Registers a URL for events: " + ", ".join(webhook_service.EVENT_TYPES) + " (or `*`). "
                         "The response includes the signing `secret`. Each delivery has the header "
                         "`Udaan-Signature: t=<unix>,v1=<HMAC-SHA256(secret, \"<t>.<raw body>\")>`.")
def create_webhook(payload: WebhookCreate, _: Principal = require("admin")):
    return webhook_service.create_subscription(payload.url, payload.events, payload.description)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(404),
               summary="Delete a webhook subscription (admin)")
def delete_webhook(webhook_id: str, _: Principal = require("admin")):
    webhook_service.delete_subscription(webhook_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/webhooks/deliveries", response_model=list[WebhookDelivery], responses=error_responses(),
            summary="Recent webhook deliveries (admin)")
def webhook_deliveries(limit: int = Query(100, ge=1, le=500), _: Principal = require("admin")):
    return webhook_service.list_deliveries(limit)
