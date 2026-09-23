# Use cases

This is every use case the system was designed for, with its actors, main flow, rules and failure cases. Each ID is
referenced in the code reviews and the feature docs. Business numbers are the defaults in `backend/app/config.py`.

**Actors:** *Guest* (no account), *Member* (Udaan Club customer), *Admin* (staff), *Agent* (an AI assistant or
integration acting through the API), *Gateway* (the hosted payment page), *Scheduler* (automatic jobs).

---

## A. Discovery and search

### UC-A1 Search one-way flights
- **Actor:** Guest, Member, Agent
- **Flow:** origin, destination, date, cabin, and counts of adults, children and infants → direct and one-stop itineraries.
- **Rules:**
  - Flights must be bookable (scheduled or delayed, not departed).
  - Connections need at least 60 min domestic / 90 min international, and at most 4 h / 24 h.
  - The cabin must exist on every segment.
  - Every flight needs seats for the adults plus children.
  - Prices shown are the adult, child and infant fares plus the party total.
  - Baggage allowances are shown per passenger type.
- **Failures:**
  - Unknown airport → 404.
  - Origin equals destination → 400.
  - More infants than adults, no adult, or more than 9 seats → 400.

### UC-A2 Search a round trip
Same as A1 for both directions. The return date is required and cannot be before the outbound date.

### UC-A3 See prices in the local currency
The UI detects the currency from the browser region and time zone, and the user can override it. Prices are
converted from USD at the sandbox rates. API clients can call `/currencies/detect`, which reads a geo-IP header or
`Accept-Language`.

### UC-A4 Read policies (Help)
Anyone can read the policy documents and the live baggage table. These documents are also the knowledge base for
a RAG assistant.

## B. Booking and payment

### UC-B1 Book as a guest
- **Flow:** create passengers (unowned) → create booking → **hold** (PNR issued, seats reserved, status PENDING,
  30-minute expiry) → hosted payment page → pay → CONFIRMED.
- **Rules:**
  - An unowned passenger can't be on another live booking; this stops people reusing strangers' passenger records.
  - Guests cannot add SSRs.

### UC-B2 Book as a member
As B1, except the passengers and the booking belong to the member, and tier benefits apply (baggage bonus, SSR eligibility).

### UC-B3 Book on behalf of a customer
An admin passes `user_id`.

### UC-B4 Pay on the hosted page
- **Flow:** open `payment_url` → enter the card → success: the session is COMPLETED, the booking is CONFIRMED, and
  webhooks `payment.succeeded` and `booking.confirmed` are sent → redirect to `success_url`.
- **Failures** (402, session stays open, `payment.failed` webhook): unknown card number, expired card, wrong CVV
  length, or missing cardholder name.
- **Conflicts** (409): the session is already paid, expired or cancelled, or the booking is no longer pending.

### UC-B5 Get a new payment link
For a PENDING booking, `POST /bookings/{id}/payment-session` (owner, admin, or last name) opens a new session,
optionally in another currency. Earlier open sessions are cancelled. The hold expiry doesn't change.

### UC-B6 Hold expiry
- **Actor:** Scheduler (every 60 seconds), also triggered before any booking or payment.
- **Effect:** a PENDING booking past its hold expiry becomes EXPIRED, its seats are released, and its sessions
  become EXPIRED. The `booking.expired` webhook is sent.

### UC-B7 Payment reported to an external system
Webhook subscribers receive signed events. `client_reference_id` and `metadata` given at booking time are echoed back,
so an agent can match the event to its conversation. See `docs/integration/payment-links-and-agents.md`.

## C. Managing a booking

### UC-C1 Retrieve a booking
- By PNR + last name (anyone).
- By booking ID (owner or admin), or booking ID + last name (anyone).
- Wrong PNR and wrong last name both return 404, so the API doesn't reveal which PNRs exist.

### UC-C2 List my trips
A member sees their bookings, newest first.

### UC-C3 Change a journey
- **Rules:**
  - The booking is active.
  - More than 24 h before the journey's first departure.
  - The new journey is between the same airports, in the same cabin.
  - It departs no more than 60 days after the original.
  - Connections and trip order stay valid, and there are enough seats.
  - Nobody is checked in on the journey.
- **Effect:** seats move, SSRs on removed flights are cancelled, the status becomes CHANGED, and the fare difference
  is recorded for information only.

### UC-C4 Cancel a booking
- **When:** before the first departure, for a PENDING or confirmed booking.
- **Effect:** seats are released, a paid booking is REFUNDED, open sessions are CANCELLED, and check-ins, tickets
  and SSRs are cancelled. The PNR is kept.

### UC-C5 Update contact details
Owner, admin, or last name.

## D. Check-in and departure

### UC-D1 Validate check-in
PNR + last name → for each segment: its phase, its check-in window (opens 48 h, closes 4 h before departure), and each
passenger's eligibility with a reason.

### UC-D2 Check in individual passengers on a flight
- **Flow:** choose a flight and passengers → seats are assigned in the booked cabin → one ticket and boarding pass per
  passenger per flight.
- **Rules:**
  - The booking is confirmed and the flight's window is open.
  - The flight is not cancelled, and the passenger isn't already checked in.
  - **An infant and the adult they are paired with check in together** on each flight.
- **Pairing:** an explicit `accompanying_adult_id` is used first; otherwise infants are paired with adults in booking order.

### UC-D3 Check in a round trip or connection
Each flight has its own window, so the outbound and return flights are checked in at different times.

### UC-D4 Change seat or offload
An offload cancels the ticket, and the passenger can check in again.

### UC-D5 Print a boarding pass
The boarding pass shows the passenger, PNR, ticket number, flight, times, boarding time (60 min before departure), cabin, seat and baggage.

### UC-D6 Follow the flight status
The phase is derived from the timeline: SCHEDULED → CHECKIN_OPEN → CHECKIN_CLOSED → BOARDING (60 min before
departure) → GATE_CLOSED (30 min) → DEPARTED → ARRIVED, or CANCELLED. DELAYED is shown alongside the phase.

## E. Special services and membership

### UC-E1 Register and log in
- Registration creates a Bronze account.
- Login (OAuth2 password grant) returns a JWT whose scopes depend on the role and tier.

### UC-E2 Request an SSR
- The token must hold `ssr:write` and `ssr:<TYPE>`; these are granted only if the tier allows that service.
- The member's current tier is re-checked, along with passenger type, flight duration and capacity, and duplicates.
- Pricing applies the tier discount or the free-service rules.

### UC-E3 See allowed services
The UI lists the services the member's token allows.

## F. Operations (admin)

### UC-F1 Create or modify a flight
- **Validation:** the route is active, the departure is in the future, and the flight number is unique for the day.
- **Aircraft rotation:** the aircraft must be free from departure until arrival plus 4 h (domestic) or 8 h (international).
- **Resizing:** a smaller aircraft must still hold the seats already sold.

### UC-F2 Generate schedules
- **How to run it:** at seed time, from the API (`POST /admin/schedules/generate`) or from the CLI (`python -m app.seed.generate_schedules`).
- **What it creates:** 3–4 flights per route per day, one in each of the morning, afternoon and night banks, plus a random extra.
- **Checks:** every flight passes the UC-F1 validation. Wide-body aircraft fly long-haul routes (3,000 km or more).
- **Output:** slots that can't be filled are skipped and reported. Existing flights are never duplicated.

### UC-F3 Manage bookings
List all bookings (guests included) with filters. View, cancel or delete them. Deleting releases seats and refunds first.

### UC-F4 Manage webhooks
Subscribe an endpoint (the response returns its signing secret), list subscriptions, delete one, and inspect deliveries.

### UC-F5 Expire holds on demand
`POST /admin/holds/expire`.

## G. Security

### UC-G1 Scope enforcement
Every protected endpoint declares its scope. A missing or invalid token → 401; a missing scope → 403.

### UC-G2 Ownership
Customers only reach their own records; anything else returns 404. Guests reach bookings through the PNR plus last
name, or through the payment session secret.

### UC-G3 Staff-only demo credentials
The sandbox accounts are listed only on `/admin/login`.
