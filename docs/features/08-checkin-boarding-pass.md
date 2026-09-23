# 08 · Check-in & boarding passes

## Purpose
Online check-in with **PNR + last name**, seat assignment, and ticket / boarding-pass issuance. Tickets are
**never** issued at booking time.

## Rules
- The booking is found by PNR and a passenger's last name; both are required.
- Check-in is per **journey** (through check-in). By default it uses the next journey that still has passengers left
  to check in (OUTBOUND first, then RETURN), and `direction` can override that. Every remaining segment of the journey
  is checked in at once.
- Eligibility: the booking is active; no flight in the journey is cancelled or departed; the **check-in window** is
  open; the passenger isn't already checked in (checking in twice returns **409**).
- Window: it opens `CHECKIN_OPENS_HOURS` before departure (default `0` = open straight after booking, which suits the
  sandbox; use 48 for airline-like behaviour) and closes `CHECKIN_CLOSES_MINUTES` (default 60) before departure.
- Seats are assigned in the booked cabin's rows (First 1–2, Business 3–14, Premium Economy 15–19, Economy 20–60),
  first free seat first. Infants get `INF` and must be checked in with, or after, an adult.
- Each passenger gets **one ticket and one boarding pass per segment**, with a 13-digit ticket number (`775…`).

## API

| Method | Path | Scope |
|---|---|---|
| POST | `/api/checkins/validate` `{pnr, last_name, direction?}` | `checkin:write` |
| POST | `/api/checkins` `{pnr, last_name, direction?, passenger_ids?}` | `checkin:write` |
| GET | `/api/checkins/{id}` | `bookings:read` (owner / admin) |
| PUT | `/api/checkins/{id}` `{seat}` or `{status: "NOT_CHECKED_IN"}` (offload → ticket cancelled) | `checkin:write` (owner / admin) |
| GET | `/api/checkins` | `admin` |
| GET | `/api/tickets/{id}?last_name=` | `bookings:read`; owner / admin, or a matching last name |
| GET | `/api/tickets/{id}/boarding-pass?last_name=` | as above; printable HTML |
| GET / POST / DELETE | `/api/tickets` | `admin` / `tickets:write` |

`validate` returns the booking view plus `direction`, `flight_ids` (the segments covered), `can_check_in`,
`eligible_passenger_ids` and `reasons`.

## Boarding pass fields
Airline, passenger (`SURNAME/GIVEN`), PNR, ticket number, flight, origin and destination, local date and time,
boarding time (45 min before departure), gate (TBA), cabin, seat and sequence number.

## UI
The Check-in page takes a PNR and last name and shows the booking with the covered segments highlighted. The user
selects passengers and confirms, then sees the boarding passes with a **Print** button; the print layout hides
everything else.
