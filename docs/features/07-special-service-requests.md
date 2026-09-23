# 07 · Special service requests (SSR)

## Purpose
Add services per passenger **per flight segment**, limited by membership tier.

## Catalog

| Type | Price | Options / constraints |
|---|---|---|
| MEAL | 15 | code `VGML`, `AVML`, `HNML`, `KSML`, `MOML`, `CHML`, `DBML`; flights of 90 min or more |
| LOUNGE | 45 | — |
| WHEELCHAIR | 0 | `WCHR`, `WCHS`, `WCHC` |
| BASSINET | 20 | infant passengers only; limited by the aircraft's `bassinet_positions` |
| EXCESS_BAGGAGE | 30 per 5 kg | quantity 1–6 |

## Tier eligibility and pricing

| Tier | Eligible | Free | Discount |
|---|---|---|---|
| Bronze | Meal, Wheelchair | Wheelchair | 0 % |
| Silver | Meal, Wheelchair, Excess baggage | Wheelchair | 10 % |
| Gold | Meal, Lounge, Wheelchair, Bassinet, Excess baggage | Wheelchair, Lounge | 20 % |

## Authorization (three layers)
1. **Token scope:** `ssr:write` plus `ssr:<TYPE>`. These are granted at login only for the types the user's tier
   allows, so a Bronze token can't create a LOUNGE request (**403**, *"Your access token does not permit LOUNGE
   requests"*).
2. **Ownership:** only the booking owner or an admin.
3. **Business rules, re-checked on the server:** the booking owner's *current* tier is eligible; the passenger is on
   the booking and of the right type; the flight is a segment of the booking and hasn't departed; the flight is long
   enough; bassinet positions remain; the quantity and option are valid; the passenger doesn't already have the same
   SSR on that flight.

## API

| Method | Path | Scope |
|---|---|---|
| GET | `/api/ssrs/catalog` | public |
| GET | `/api/fares/ssr/{type}?tier_id=&quantity=` | public |
| GET | `/api/ssrs/available?booking_id=&passenger_id=&flight_id=` | `ssr:read` |
| GET | `/api/ssrs`, `/api/ssrs/{id}` | `ssr:read` |
| POST | `/api/ssrs` `{booking_id, passenger_id, flight_id?, type, quantity?, option?, notes?}` | `ssr:write` + `ssr:<TYPE>` |
| DELETE | `/api/ssrs/{id}` (sets status CANCELLED) | `ssr:write` |

If `flight_id` is omitted, the SSR goes on the first segment that hasn't departed. Changing a journey cancels the
SSRs on flights that were removed.

## UI
The booking UI doesn't offer SSRs. My Booking lists the services the user's token allows; requests go through the API.
