"""Currencies, webhooks, schedule generation and policy documents."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class Currency(BaseModel):
    code: str
    name: str
    rate: float = Field(description="Units per 1 USD (sandbox reference rate)")
    decimals: int


class CurrencyDetection(BaseModel):
    country: str | None
    currency: str
    source: str = Field(description="geo-header, accept-language or default")


class WebhookCreate(BaseModel):
    url: str = Field(examples=["https://agent.example.com/hooks/udaan"])
    events: list[str] = Field(default_factory=lambda: ["*"], examples=[["payment.succeeded", "booking.confirmed"]])
    description: str | None = None


class Webhook(BaseModel):
    webhook_id: str
    url: str
    events: list[str]
    description: str | None = None
    secret: str = Field(description="Signing secret for verifying the Udaan-Signature header")
    active: bool
    created_at: datetime


class WebhookDelivery(BaseModel):
    delivery_id: str
    webhook_id: str
    event_id: str
    event_type: str
    url: str
    status_code: int | None
    success: bool
    error: str | None
    delivered_at: datetime


class ScheduleGenerateRequest(BaseModel):
    start_date: date | None = Field(default=None, description="Default: tomorrow")
    days: int = Field(default=60, ge=1, le=120)
    min_per_route: int = Field(default=3, ge=1, le=6)
    max_per_route: int = Field(default=4, ge=1, le=6)
    seed: int | None = Field(default=None, description="Random seed for reproducible schedules")
    route_ids: list[str] | None = Field(default=None, description="Limit to these routes")


class ScheduleGenerateResult(BaseModel):
    start_date: date
    end_date: date
    routes: int
    created: int
    skipped: int
    skipped_reasons: dict[str, int]
    average_flights_per_day: float


class PolicyDocumentSummary(BaseModel):
    slug: str = Field(examples=["baggage"])
    title: str


class PolicyDocument(PolicyDocumentSummary):
    content: str = Field(description="Markdown")
