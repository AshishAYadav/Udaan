# Udaan Airlines — Booking & Servicing Sandbox

A prototype airline booking and servicing system. It is a **FastAPI** monolith with a **TinyDB** JSON database and a
**React + Tailwind** UI, secured with **OAuth2 + JWT** scopes.

It covers:
- guest checkout (no account needed) and member accounts with tier benefits;
- one-way and round-trip search with one-stop connections and adult / child / infant fares;
- multi-segment bookings with PNRs, retrieved by PNR or booking ID plus last name;
- seat holds and a hosted payment page (payment links) with sandbox test cards, local currencies and signed webhooks;
- baggage allowances by route, cabin and passenger type;
- journey changes and cancellation;
- tier-based special service requests (SSRs);
- per-flight, per-passenger check-in with live flight phases and boarding passes;
- about 4,600 generated flights (22 routes × 3–4 a day × 60 days) with realistic aircraft rotation, plus booking and webhook administration.

> This is a sandbox. Payments, PNRs and tickets are simulated and are not real airline records.

## Documentation
- [docs/features/](docs/features/README.md) — one document per feature (rules, API, UI, configuration)
- [docs/API.md](docs/API.md) — endpoint reference and the end-to-end flow with curl
- [docs/design/use-cases.md](docs/design/use-cases.md) · [docs/design/conventions.md](docs/design/conventions.md) — the use cases and conventions behind the design
- [docs/policies/](docs/policies/README.md) — customer policies: the Help page content, ready for RAG
- [docs/integration/payment-links-and-agents.md](docs/integration/payment-links-and-agents.md) — payment links and webhooks for MCP/LLM agents
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
├── seed/            Seed data, seeder and generate_schedules CLI
└── utils/           Errors, time helpers, ID/PNR generation
frontend/src
├── services/api.js  API service layer (bearer token, error handling)
├── hooks/           useAuth (token + scopes), useAsync (loading/error)
├── components/      BookingView, ItineraryCard, BoardingPass, FlightForm, RequireAuth, …
└── pages/           Login, Search, Book, PaymentPage (UdaanPay), Manage booking, Check-in, Help, Admin
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
1. On the home page choose **Round trip**, for example DEL → LHR, with 2 adults and 1 infant → **Search flights**.
   You don't need to log in, and prices appear in your local currency (change it in the top bar).
2. Pick an outbound and a return itinerary → **Continue**. The baggage allowance is shown on every option.
3. Fill in the passengers → Review → **Continue to secure payment**. Your seats are held for 30 minutes and you land
   on the **UdaanPay** page.
4. Pay with a test card, for example `4111 1111 1111 1111`, expiry `12/30`, CVV `123`. The list is on the page.
   You are sent back to Manage booking with the booking confirmed.
5. **Check-in** (for flights within 48 h): enter the PNR and last name, then tick passengers per flight. An adult and
   their infant go together. Print the boarding passes.
6. **Help** has the baggage, check-in, fares, payments and change policies.
7. **Staff sign in** (footer, `admin` / `admin`) → Admin → Flights (including **Generate schedules**) or Bookings.

## Key business rules
- **Booking:** book from tomorrow up to 60 days ahead. Seats are held for 30 minutes until paid; holds that aren't paid expire and release their seats.
- **Guests** book, pay, manage and check in with the PNR + last name. SSRs need a member account.
- **Connections:** at least 60 min domestic / 90 min international between flights, and at most 4 h domestic / 24 h international.
- **Fares:** child 75%, infant 10% (on lap, one per adult). Baggage: domestic Economy 1 × 15 kg checked + 7 kg cabin + a personal item; infants 5 kg cabin only.
- **Check-in:** opens 48 h and closes 4 h before each flight. Boarding runs from 60 min, and the gate closes at 30 min.
- **Changes:** more than 24 h before departure, to a journey departing within 60 days of the original.
- **Aircraft rotation:** an aircraft is busy until arrival plus 4 h (domestic) or 8 h (international).
- **Security:** a scope per endpoint, and customers only reach their own records. SSR scopes are granted per tier.

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `data/airline.json` | TinyDB file |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origins (comma-separated) |
| `SEED_DAYS` | `60` | Days of schedules generated |
| `JWT_SECRET` | dev value | JWT signing secret |
| `ACCESS_TOKEN_MINUTES` | `60` | Token lifetime |
| `MIN_CONNECTION_*`, `MAX_CONNECTION_*` | 60 / 90 min, 4 / 24 h | Connection rules |
| `CHECKIN_OPENS_HOURS` / `CHECKIN_CLOSES_MINUTES` | `48` / `240` | Check-in window |
| `BOARDING_OPENS_MINUTES` / `BOARDING_CLOSES_MINUTES` | `60` / `30` | Boarding and gate-close times |
| `BOOKING_HOLD_MINUTES` | `30` | Unpaid seat hold |
| `CHANGE_WINDOW_DAYS` | `60` | Latest new departure after a change |
| `PUBLIC_UI_URL` | `http://localhost:5173` | Base of hosted payment links |
| `SEED_RANDOM_SEED` | `2026` | Reproducible generated schedules |
