"""Udaan Airlines sandbox — FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api import (
    admin,
    aircrafts,
    airports,
    auth,
    bookings,
    checkins,
    checkout,
    classes,
    currencies,
    fares,
    flights,
    itineraries,
    passengers,
    payments,
    policies,
    routes,
    ssrs,
    tickets,
    tiers,
    users,
)
from app.config import settings
from app.db.database import close_db
from app.seed.seeder import init_database
from app.services import booking_service
from app.utils.errors import DomainError

DESCRIPTION = """
Sandbox airline booking and servicing API for **Udaan Airlines** (prototype — PNRs, tickets and payments are simulated).

### Authentication
OAuth2 **password flow** issuing signed **JWT** bearer tokens (click **Authorize**). Each endpoint lists the scope it
needs. Customers only get `ssr:<TYPE>` scopes for the services their tier allows. Reference data, search, and the
booking, hosted payment, PNR and check-in flow are also open to **guests** without a token. The payment
page is secured by its secret session URL, and a booking by the PNR plus a passenger's last name.

### Booking flow
1. `GET /api/itineraries/search` — one-way or round trip, direct or one-stop, fares and baggage by passenger type
2. `POST /api/passengers` — create each passenger
3. `POST /api/bookings` — **hold** seats, get the **PNR** and a hosted `payment_url` (booking status PENDING)
4. Payer opens `payment_url` (UI `/pay/{session_id}`), or call `POST /api/payment-sessions/{session_id}/pay` with a test card
   → booking **CONFIRMED**; webhooks `payment.succeeded` + `booking.confirmed` go to subscribed endpoints
5. `GET /api/bookings/pnr/{pnr}?last_name=...` — retrieve the itinerary
6. (optional) `POST /api/bookings/{id}/payment-session` — a new payment link for a held booking
7. `POST /api/checkins/validate`, then `POST /api/checkins` — per passenger, per flight, inside the check-in window
8. `GET /api/tickets/{ticket_id}` — boarding pass

Errors are returned as `{"detail": "..."}`. The status codes are: 400 business rule, 401 not authenticated, 403 missing
scope or not your resource, 404 not found, 409 conflict, 422 schema validation.
"""

TAGS = [
    {"name": "Authentication", "description": "OAuth2 password flow, registration and profile"},
    {"name": "Itineraries", "description": "One-way / round-trip search with connections"},
    {"name": "Flights", "description": "Search, schedules and schedule administration"},
    {"name": "Fares", "description": "Flight fares and SSR pricing"},
    {"name": "Passengers", "description": "Adult / child / infant passenger records"},
    {"name": "Payments", "description": "Payment sessions and attempts"},
    {"name": "Checkout (hosted payment page)", "description": "Public endpoints behind the hosted payment URL"},
    {"name": "Currencies", "description": "Point-of-sale currencies and detection"},
    {"name": "Policies & help", "description": "Policy documents and baggage allowances"},
    {"name": "Bookings", "description": "Bookings, PNR lookup, change and cancellation"},
    {"name": "Check-in", "description": "PNR + last name check-in and ticket issuance"},
    {"name": "Tickets", "description": "Tickets and boarding passes (issued only after check-in)"},
    {"name": "Special service requests", "description": "Meals, lounge, wheelchair, bassinet, excess baggage"},
    {"name": "Routes", "description": "Valid routes, source and destination airports"},
    {"name": "Airports", "description": "Airport reference data"},
    {"name": "Cabin classes", "description": "Cabin classes and availability"},
    {"name": "Aircraft", "description": "Fleet and aircraft availability"},
    {"name": "Users", "description": "Users and their membership tier"},
    {"name": "Tiers", "description": "Membership tier levels"},
    {"name": "Admin", "description": "Dashboard aggregates"},
]


async def _expire_holds_periodically() -> None:
    while True:
        await asyncio.sleep(60)
        await asyncio.to_thread(booking_service.expire_holds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    task = asyncio.create_task(_expire_holds_periodically())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    close_db()


app = FastAPI(
    title="Udaan Airlines Sandbox API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


for module in (auth, itineraries, flights, fares, checkout, currencies, policies, passengers, payments, bookings, checkins, tickets, ssrs,
               routes, airports, classes, aircrafts, users, tiers, admin):
    app.include_router(module.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/api/health", tags=["Admin"], summary="Health check (public)")
def health():
    return {"status": "ok"}
