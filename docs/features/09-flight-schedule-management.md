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
