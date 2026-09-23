# 04 · Payments (mock gateway)

## Purpose
Simulate payment without a real provider, and let the caller choose the outcome, so both booking paths can be tested.

## State machine
```
PENDING ──APPROVE──▶ APPROVED ──complete──▶ COMPLETED ──booking cancelled──▶ REFUNDED
PENDING ──REJECT───▶ REJECTED ──complete──▶ FAILED
```
Only a `COMPLETED` payment can confirm a booking, and only once. A rejected or failed payment makes booking creation
fail with *"Payment was rejected. The booking is not confirmed and no seats were reserved."* No seats are used.

## Pricing
The **server** calculates the amount from the trip (the client never sends it). For each segment and each
passenger: adult 100%, child 75%, infant 10% of the cabin's base fare. `breakdown[]` lists one line per passenger per
segment. When a payment is created, the connections, trip order, party rules, passenger ownership and seats are all
validated.

## API

| Method | Path | Scope |
|---|---|---|
| POST | `/api/payments` `{outbound_flight_ids, return_flight_ids, class_id, passenger_ids, method?, user_id? (admin)}` | `payments:write` |
| PUT | `/api/payments/{id}` `{"action": "APPROVE" \| "REJECT"}` | `payments:write` |
| POST | `/api/payments/{id}/complete` | `payments:write` |
| GET | `/api/payments/{id}` · `/api/payments/{id}/status` | `bookings:read` |

Customers can only see and act on their own payments; any other payment returns 404. **Guests** use the payment's
`access_key`, returned in the create response: they send it as the `X-Payment-Key` header, and as `payment_key` when
booking. No card data is accepted or stored.

## Code
`services/payment_service.py`.
