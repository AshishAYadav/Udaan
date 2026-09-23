# 02 · Flight search & itineraries

## Purpose
Find bookable one-way or round-trip itineraries, direct or with **one connection**, in a single request.

## Rules
An **itinerary** (journey) is one flight, or two connecting flights, from the origin to the destination.

A connection is valid when:
1. the second flight leaves from the airport where the first arrives;
2. the layover is **at least the minimum connecting time (MCT)**: 60 min domestic, 90 min international;
3. the layover is **no longer than the maximum connection time**: 4 h domestic, 24 h international. A longer
   layover is a *stopover* and is not offered as a connection (the IATA 24 h stopover convention);
4. the journey never visits an airport twice.

A connection counts as *domestic* only when both flights are domestic (same country).

A **round trip** is an outbound journey plus a return journey that reverses it, on the return date the user picks.
The return must depart after the outbound arrives, with at least the MCT in between. Both journeys go into **one
booking and one PNR**.

Only cabins that exist on **every** segment and have at least `passengers` seats are offered. The price shown is the
adult fare summed over the segments. Flights that have departed or are cancelled are excluded.

## API

`GET /api/itineraries/search` (public)

| Param | Required | Description |
|---|---|---|
| `origin`, `destination` | yes | IATA codes |
| `date` | yes | outbound local departure date |
| `return_date` | no | return local departure date; makes it a round trip |
| `cabin_class` | no | limit to one cabin |
| `adults` | no | 12+ years, default 1 |
| `children` | no | 2–11 years, 75 % fare, own seat |
| `infants` | no | under 2, 10 % fare, on an adult's lap (at most one per adult) |

The response is `{trip_type, outbound: [Itinerary], return: [Itinerary]}`. Each itinerary has `flight_ids`, `stops`,
`segments`, `layovers` (airport and minutes), `total_duration_minutes`, `available_classes` and `starting_fare`.
Each entry in `available_classes` has `price` (adult), `child_price`, `infant_price`, `party_total` (the whole party)
and `available_seats`; all prices are summed over the segments. The response also echoes the `party`. Only cabins with
enough seats for the adults and children are offered. Pass `flight_ids` as `outbound_flight_ids` / `return_flight_ids` when paying and
booking.

`GET /api/flights/search` still returns **direct** flights only.

```bash
curl "localhost:8000/api/itineraries/search?origin=DEL&destination=LHR&date=2026-09-25&return_date=2026-09-28"
# outbound: FLT008-FLT009  DEL 11:00 → DXB, 175 min connection → LHR
# return:   FLT021-FLT025  LHR 08:00 → DXB, 180 min connection → DEL
```

## Seeded network
The timetable (`seed/data.py → TIMETABLE`) runs two daily banks that alternate by calendar date and connect:
- even dates: BLR 06:00 → DEL · DEL 11:00 → DXB · DXB 16:00 → LHR · LHR 22:30 → JFK · BOM 09:00 → SIN
- odd dates: LHR 08:00 → DXB · DXB 21:00 → DEL · DEL 17:00 → BLR · JFK 18:00 → LHR · SIN 09:00 → BOM

For example, DEL→LHR (via DXB), BLR→DXB (via DEL) and DXB→JFK (via LHR) connect on even dates; LHR→DEL (via DXB) connects on odd dates.

## Configuration
`MIN_CONNECTION_DOMESTIC_MINUTES` (60), `MIN_CONNECTION_INTERNATIONAL_MINUTES` (90),
`MAX_CONNECTION_DOMESTIC_HOURS` (4), `MAX_CONNECTION_INTERNATIONAL_HOURS` (24). `MAX_STOPS = 1` is set in
`itinerary_service.py`.

## Code
`services/itinerary_service.py`: `connection_error`, `load_journey`, `validate_trip`, `prepare_trip`, `search_trip`.
