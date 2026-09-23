# Feature documentation

Each document covers one feature: its purpose, business rules, API, UI, data model and configuration.

| # | Feature | Summary |
|---|---|---|
| 01 | [Authentication & authorization](01-authentication-authorization.md) | OAuth2 password flow, JWT, scopes, tier-based SSR scopes, ownership |
| 02 | [Flight search & itineraries](02-flight-search-itineraries.md) | One-way / round trip, direct and one-stop connections |
| 03 | [Booking & PNR retrieval](03-booking-pnr.md) | Segments, PNR generation, PNR / booking ID + last name |
| 04 | [Payments](04-payments.md) | Holds, hosted payment page, test cards, webhooks |
| 05 | [Booking change & cancellation](05-booking-change-cancellation.md) | 24 h / 7 day journey change, cancellation and refund |
| 06 | [Passengers](06-passengers.md) | Adult / child / infant rules and ownership |
| 07 | [Special service requests](07-special-service-requests.md) | Tier eligibility, per-segment SSRs |
| 08 | [Check-in & boarding passes](08-checkin-boarding-pass.md) | Per-flight windows, individual check-in, infant rule, flight phases |
| 09 | [Flight schedule management](09-flight-schedule-management.md) | Admin schedules, aircraft rotation, automatic generator |
| 10 | [Reference data & tiers](10-reference-data-tiers.md) | Airports, routes, aircraft, cabins, tiers, seed data |
| 11 | [Web UI](11-web-ui.md) | Customer and admin screens |
| 12 | [Baggage](12-baggage.md) | Allowances by route, cabin, passenger type and tier |
| 13 | [Currency](13-currency.md) | Local-currency pricing and detection |

Related documents:
- [Use cases](../design/use-cases.md)
- [Conventions](../design/conventions.md)
- [Customer policies](../policies/README.md) — the source for the Help page and RAG
- [Payment links, webhooks and AI agents](../integration/payment-links-and-agents.md)

All settings mentioned in these documents live in `backend/app/config.py`. Some can be overridden from `.env`.
