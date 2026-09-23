# 10 · Reference data, tiers & seed data

## Collections (TinyDB, `data/airline.json`)
`users`, `tiers`, `airports`, `routes`, `aircrafts`, `classes`, `flights`, `fares` (seat inventory per flight and
cabin), `passengers`, `payments`, `bookings`, `booking_history`, `ssr_catalog`, `specialservicerequests`, `checkins`,
`tickets`, `counters` (sequential IDs), and `meta` (schema version).

## Seed data (created automatically)
- **12 airports** (DXB, LHR, JFK, DEL, BOM, BLR, SIN, CDG, FRA, DOH, SYD, HND) with IANA timezones.
- **14 routes**: 10 of them run on the timetable in [02](02-flight-search-itineraries.md); 4 are valid routes with no scheduled flights.
- **15 aircraft** across five types (A350-900, B787-9, A321neo, B777-300ER, A320neo), each with its cabin layout and bassinet positions.
- **4 cabins**, **3 tiers**, **1 admin and 6 customers** (see [01](01-authentication-authorization.md)), and the **SSR catalog**.
- **60 days × 5 flights per day** starting tomorrow, with fares for every cabin. Every seeded flight satisfies the
  aircraft rotation rule, and each aircraft flies every third day.

The database is rebuilt automatically when `SCHEMA_VERSION` in `seed/seeder.py` changes. Rebuild it by hand with
`python -m app.seed.seeder --reset`.

## Tier data
`tier_id`, `name`, `priority`, `eligible_ssrs`, `free_ssrs`, `ssr_discount_percent`, `extra_baggage_kg`, `benefits`.
Tiers decide both SSR eligibility and the SSR scopes put in the token.

## Public API
`/api/airports`, `/api/routes` (`/valid`, `/sources`, `/destinations?origin=`), `/api/classes`
(`/available?flight_id=`), `/api/tiers`, `/api/fares/flight/{id}`. Admin only: `/api/users`, `/api/aircrafts`, `/api/admin/summary`.
