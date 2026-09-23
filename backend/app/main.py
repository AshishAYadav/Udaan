"""Udaan Airlines sandbox — FastAPI application entry point."""
from contextlib import asynccontextmanager

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
    classes,
    fares,
    flights,
    itineraries,
    passengers,
    payments,
    routes,
    ssrs,
    tickets,
    tiers,
    users,
)
from app.config import settings
from app.db.database import close_db
from app.seed.seeder import init_database
from app.utils.errors import DomainError

DESCRIPTION = """
Sandbox airline booking and servicing API for **Udaan Airlines** (prototype — PNRs, tickets and payments are simulated).

### Authentication
OAuth2 **password flow** issuing signed **JWT** bearer tokens (click **Authorize**). Each endpoint lists the scope it
needs. Customers only get `ssr:<TYPE>` scopes for the services their tier allows. Reference data, search, and the
booking, payment, PNR and check-in flow are also open to **guests** without a token. A guest's payment is secured by
its `access_key`, and a guest's booking by the PNR plus a passenger's last name.

### Booking flow
1. `GET /api/itineraries/search` — one-way or round trip, direct or one-stop
2. `POST /api/passengers` — create each passenger
3. `POST /api/payments` — create a PENDING payment for the chosen flights (amount computed by the server)
4. `PUT /api/payments/{id}` with `{"action": "APPROVE"}` (or `REJECT`), then `POST /api/payments/{id}/complete`
5. `POST /api/bookings` — confirm the booking and receive a **PNR**
6. `GET /api/bookings/pnr/{pnr}?last_name=...` — retrieve the itinerary (PNR + last name)
7. `POST /api/checkins/validate`, then `POST /api/checkins` — through check-in; one ticket per passenger per segment
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
    {"name": "Payments", "description": "Mock payment gateway with approve / reject"},
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield
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


for module in (auth, itineraries, flights, fares, passengers, payments, bookings, checkins, tickets, ssrs,
               routes, airports, classes, aircrafts, users, tiers, admin):
    app.include_router(module.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/api/health", tags=["Admin"], summary="Health check (public)")
def health():
    return {"status": "ok"}
