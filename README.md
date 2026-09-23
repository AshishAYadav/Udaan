# Udaan Airlines — Booking & Servicing Sandbox

A prototype airline booking and servicing system. It is a **FastAPI** monolith with a **TinyDB** JSON database and a
**React + Tailwind** UI, secured with **OAuth2 + JWT** scopes.

It covers:
- guest checkout (no account needed) and member accounts with tier benefits;
- one-way and round-trip search with one-stop connections and adult / child / infant fares;
- multi-segment bookings with PNRs, retrieved by PNR or booking ID plus last name;
- mock payments;
- journey changes and cancellation;
- tier-based special service requests (SSRs);
- through check-in with boarding passes;
- flight schedule and booking administration (list, cancel, delete) with realistic aircraft rotation.

> This is a sandbox. Payments, PNRs and tickets are simulated and are not real airline records.

## Documentation
- [docs/features/](docs/features/README.md) — one document per feature (rules, API, UI, configuration)
- [docs/API.md](docs/API.md) — endpoint reference and the end-to-end flow with curl
- Swagger: <http://localhost:8000/docs> · ReDoc: <http://localhost:8000/redoc>

## Architecture

```
backend/app
├── main.py          FastAPI app, CORS, error handler, router registration
├── config.py        Settings (.env) and business-rule constants
├── auth/            JWT + password hashing, OAuth2 scopes, Principal dependency
├── api/             Thin routers (one per resource) with OpenAPI docs and scope requirements
├── services/        Business rules (itinerary, booking, payment, check-in, SSR, flights, auth, …)
├── schemas/         Pydantic request/response models
├── models/enums.py  Status, role and type enumerations
├── db/database.py   Central TinyDB access: repositories, locking, ID counters
├── seed/            Deterministic seed data, timetable and seeder
└── utils/           Errors, time helpers, ID/PNR generation
frontend/src
├── services/api.js  API service layer (bearer token, error handling)
├── hooks/           useAuth (token + scopes), useAsync (loading/error)
├── components/      BookingView, ItineraryCard, BoardingPass, FlightForm, RequireAuth, …
└── pages/           Login, Search, Book, My Booking, Check-in, Admin
data/airline.json    TinyDB database (created on first start)
```

Requests flow **router → service → repository (TinyDB)**. Multi-step operations, such as checking seats on every
segment and then reserving them, run under a single lock.

## Setup

Requirements: Python 3.11+ and Node.js 18+.

```bash
cp .env.example .env            # optional; set JWT_SECRET for shared environments
```

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The first start seeds the database. It is re-seeded automatically when the schema version changes, and you can
rebuild it with `python -m app.seed.seeder --reset`.

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api and /docs to :8000)
npm run build
```

## Accounts
Customers create their own accounts (`/login` → Create account) or book as guests. The seeded accounts below are
listed only on the staff sign-in page, `/admin/login`.

| Username | Password | Role / tier |
|---|---|---|
| `admin` | `admin` | Admin — all scopes |
| `john`, `emma` | `password123` | Gold |
| `priya`, `sofia` | `password123` | Silver |
| `ahmed`, `rahul` | `password123` | Bronze |

New members start in the Bronze tier.

## Try it (UI)
1. On the home page, choose **Round trip**, DEL → LHR on an **even** date returning on an odd date, and 2 adults +
   1 child → **Search flights**. You don't need to log in.
2. Pick the one-stop itineraries via DXB → **Continue**.
3. Add passengers → Review → choose **Approve** → **Complete payment** → the PNR is shown.
4. **Check-in** → PNR + last name → confirm. You get boarding passes for both outbound segments → **Print**.
   Check in again later for the return journey.
5. **Staff sign in** (footer link, `admin` / `admin`) → Admin → **Manage flights** or **Manage bookings** (list, view, cancel, delete).

## Key business rules
- **Guests** book, manage and check in with the PNR + last name. A payment is secured by its access key. SSRs need a member account.
- **Retrieval:** PNR + last name, or booking ID + last name. Only the owner or an admin can skip the last name.
- **Connections:** at least 60 min domestic / 90 min international between flights, and at most 4 h domestic /
  24 h international (a longer gap is a stopover). A round trip is one booking and one PNR.
- **Aircraft rotation:** an aircraft is busy from departure until arrival plus 4 h (domestic) or 8 h (international).
- **Changes:** more than 24 h before departure, to a journey departing within 7 days of the original.
- **Tickets** are issued only at check-in, one per passenger per segment.
- **Security:** each endpoint needs a scope, and customers only reach their own records. SSR write scopes are granted
  per tier, so an ineligible user's token cannot create that service.

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `data/airline.json` | TinyDB file |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origins (comma-separated) |
| `SEED_DAYS` | `60` | Days of schedules generated |
| `JWT_SECRET` | dev value | JWT signing secret |
| `ACCESS_TOKEN_MINUTES` | `60` | Token lifetime |
| `MIN_CONNECTION_*`, `MAX_CONNECTION_*` | 60 / 90 min, 4 / 24 h | Connection rules |
| `CHECKIN_OPENS_HOURS` / `CHECKIN_CLOSES_MINUTES` | `0` (always open) / `60` | Check-in window |
