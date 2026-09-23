# 08 · Check-in, flight phases and boarding passes

## Rules
- **Lookup:** PNR + a passenger's last name (guests and members).
- **Window per flight:** check-in opens **48 h** before each segment's departure and closes **4 h** before it.
  Outbound and return flights (and each leg of a connection) are checked in separately.
- **Booking:** must be CONFIRMED or CHANGED. A PENDING booking must be paid first.
- **Individual check-in:** any subset of passengers can check in on a flight.
- **Infant rule:** an infant and the adult they are paired with must check in together on that flight. An explicit
  `accompanying_adult_id` is used first; otherwise adults are paired with infants in booking order.
- **Seats:** assigned in the booked cabin's rows (First 1–2, Business 3–14, Premium Economy 15–19, Economy 20–60). Infants get `INF`.
- **Tickets:** **one ticket and boarding pass per passenger per flight**, issued at check-in and never at booking.
- **Duplicates:** checking a passenger in twice on the same flight returns 409.

## Flight phase (live status)
The phase comes from the stored status and the clock:

| Phase | When |
|---|---|
| `SCHEDULED` | Before check-in opens (more than 48 h out) |
| `CHECKIN_OPEN` | 48 h to 4 h before departure |
| `CHECKIN_CLOSED` | 4 h to 60 min before departure |
| `BOARDING` | 60 to 30 min before departure |
| `GATE_CLOSED` | Less than 30 min before departure |
| `DEPARTED` | After departure (or the status was set to DEPARTED) |
| `ARRIVED` | After arrival |
| `CANCELLED` | The flight status is CANCELLED |

`phase` appears on flight summaries, schedules, the booking view, check-in validation and the boarding pass.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/checkins/validate` `{pnr, last_name}` | For each segment: phase, `checkin_opens_at` / `closes_at`, `open`, `reason`, and each passenger's `eligible`, `reason` and `travels_with` |
| POST | `/api/checkins` `{pnr, last_name, flight_ids?, passenger_ids?}` | Defaults: every open flight and every passenger not yet checked in |
| PUT | `/api/checkins/{id}` | Change seat, or offload (the ticket is cancelled) |
| GET | `/api/tickets/{id}?last_name=` | Boarding pass, including `baggage` and `phase` |

## Configuration
`CHECKIN_OPENS_HOURS` (48), `CHECKIN_CLOSES_MINUTES` (240), `BOARDING_OPENS_MINUTES` (60), `BOARDING_CLOSES_MINUTES` (30).

## UI
The Check-in page shows one card per flight, with its phase, window and passenger checkboxes. Ticking an adult or
their infant ticks both. A "Check in N passenger(s) on UD102" button submits the card, and the boarding passes are printable.
