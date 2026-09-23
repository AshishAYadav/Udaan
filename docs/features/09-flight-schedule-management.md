# 09 · Flight schedule management

## Purpose
Let admins create and modify dated flights while keeping aircraft rotations realistic.

## Aircraft rotation rule
An aircraft is **busy from departure until arrival plus the minimum ground (turnaround) time**:

| Flight | Minimum ground time after arrival |
|---|---|
| Domestic (same country) | **4 hours** |
| International | **8 hours** |

A new or changed flight is rejected with **409** if its busy window overlaps another flight's on the same aircraft
(cancelled flights are ignored). For example, a DXB→LHR flight (7 h 30) departing 16:00 GST keeps its aircraft busy
until 8 hours after it lands in London. After that, the aircraft can be scheduled again, for example back on the same
route.

> The rule checks *time*, not *position*: it doesn't require the next departure to leave from the previous arrival
> airport. That would be the natural next refinement, via tail assignment.

## Automatic schedule generation
`services/schedule_generator.py` creates **3–4 flights per active route per day**: one in each of the morning
(06:00–11:45), afternoon (12:00–17:45) and night (18:00–23:30) banks, plus a random extra, at quarter-hour times at
least 60 minutes apart.

Every generated flight passes the same validation as manual scheduling:
- the route is active and both airports exist;
- the departure is in the future;
- `UD<slot><route no>` is unique that day;
- an aircraft is free for departure → arrival + ground time.

Wide-bodies (250 seats or more) fly routes of 3,000 km or more, and narrow-bodies fly the rest. A slot with no
available aircraft is **skipped and reported**, never forced. Results are reproducible with `seed`.

| How | Command |
|---|---|
| Seeding | Automatic: `SEED_DAYS` (60) days from tomorrow, `SEED_RANDOM_SEED` |
| API (admin) | `POST /api/admin/schedules/generate` `{start_date?, days, min_per_route, max_per_route, seed?, route_ids?}` |
| CLI | `python -m app.seed.generate_schedules --days 60 [--start YYYY-MM-DD] [--seed N]` |
| UI | Admin → Flights → **Generate schedules** |

The response reports `created`, `skipped` and `skipped_reasons` (for example `"no aircraft available"` or
`"flight number already operating that day"`), plus `average_flights_per_day`. Running it again over the same dates
adds nothing, because the flight numbers already exist.

## Other rules
- The route must be active, and the departure must be in the future.
- A departure time without an offset is read as **origin local time**. The arrival is calculated from the route
  duration, in the destination's timezone.
- A flight number can't operate twice on the same local date.
- Fares are created for every cabin on the aircraft, either at a default price (distance-based, +10% at weekends) or
  from `fares` in the request.
- Moving a flight to a different aircraft keeps the seats already sold. The new aircraft needs enough seats in each
  cabin (**409** otherwise).
- Statuses: `SCHEDULED`, `DELAYED`, `DEPARTED`, `CANCELLED`. DEPARTED and CANCELLED flights can only have their
  status changed.

## API

| Method | Path | Scope |
|---|---|---|
| GET | `/api/flights`, `/api/flights/{id}` | public |
| GET | `/api/flights/schedules` (paged, with seats sold and available) | `admin` |
| POST | `/api/flights/schedules` `{flight_number, route_id, aircraft_id, departure_time, fares?}` | `flights:write` |
| PUT | `/api/flights/schedules/{id}` `{flight_number?, aircraft_id?, departure_time?, status?}` | `flights:write` |
| GET | `/api/aircrafts/available?route_id=&departure_time=` | `admin` |

## Configuration
`turnaround_domestic_hours` (4), `turnaround_international_hours` (8).

## UI
Admin → Flights has a filterable, paged table and Add / Edit forms. Rule violations appear as error messages in the form.
