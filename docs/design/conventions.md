# Conventions

## Domain and airline conventions
- **PNR:** 6 characters from `A–Z 2–9`, without `0 O 1 I`. It is issued when the booking is held and becomes valid for travel once paid.
- **Ticket number:** 13 digits — airline prefix `775` plus a 10-digit serial. Tickets are issued per passenger per flight, at check-in only.
- **Flight numbers:** `UD<slot><route no>`. For example, `UD107` is the first departure of the day on route RT007.
- **Passenger types:** decided by age on the first departure date. Under 2 is an INFANT, 2–11 a CHILD, 12 or older an ADULT.
- **Fare factors:** child 75%, infant 10% (lap, no seat). At most one infant per adult, at least one adult per booking.
- **Connections:** MCT is 60 min domestic / 90 min international. The maximum is 4 h / 24 h (IATA stopover convention). At most 1 stop.
- **Aircraft rotation:** an aircraft is busy from departure to arrival plus ground time (4 h domestic / 8 h international).
- **Departure timeline:**
  - check-in opens T-48 h and closes T-4 h;
  - boarding runs from T-60 min;
  - the gate closes at T-30 min.
- **Baggage:** the piece concept with a per-piece weight. A journey is domestic only if every segment is domestic.
- **Holds:** unpaid bookings hold seats for 30 minutes.

## API conventions
- **Paths:** REST under `/api`, with plural resource names. Actions are sub-resources: `/bookings/{id}/cancel`, `/payment-sessions/{id}/pay`.
- **Identifiers:** sequential with a prefix (`BK001`, `FLT1234`, …). Secrets use random tokens: `ps_…` for payment sessions, `whsec_…` for webhook secrets.
- **Errors:** always `{"detail": "..."}`, with these status codes:

  | Status | Used for |
  |---|---|
  | 400 | Business rule |
  | 401 | Authentication |
  | 402 | Card declined |
  | 403 | Scope or ownership |
  | 404 | Not found, or hidden |
  | 409 | State conflict |
  | 422 | Schema |

- **Times:** ISO-8601 with an offset. Flight times are in the airport's local time; system timestamps are UTC. Search dates are local departure dates.
- **Money:** fares are in USD (`base_amount`). A booking and its payment carry `currency`, `total_amount` / `amount` and the `exchange_rate` used.
- **Auth:** OAuth2 password grant with HS256 JWTs. Scopes follow `resource:action`; SSR scopes are `ssr:<TYPE>`. Endpoints open to guests use an optional bearer token.
- **Webhooks:** event names are `resource.event`. Deliveries carry `Udaan-Signature: t=<unix>,v1=<hmac>`.
- **Idempotency:** paying a completed session returns 409, and schedule generation skips flight numbers that already operate that day.

## Code conventions
- **Layers:** router (thin, with OpenAPI docs) → service (business rules) → repository (TinyDB).
- **Transactions:** multi-step writes use `with transaction():`, which serialises them and flushes the database once at the end.
- **Data ownership:** services receive the caller as `Principal | None` (None = guest). Ownership checks use `owns(actor, user_id)`.
- **Configuration:** all business numbers live in `config.py` and can be overridden with environment variables. The policy documents must be kept in step with them.
- **Frontend:** API calls go only through `services/api.js`. Shared state lives in the `useAuth` and `useCurrency` contexts, and every page handles loading and error states.
