# 04 · Payments (hosted checkout)

## Purpose
Take payment the way modern systems do: a **hosted payment page** reached through a secret link, **test-card
validation**, and **signed webhooks**. An agent, website or back office can create the link and learn the outcome
later. See the [integration guide](../integration/payment-links-and-agents.md).

## Lifecycle
```
POST /bookings ──▶ booking PENDING (PNR, seats held 30 min) + payment session PENDING (payment_url)
      payer pays ──▶ session COMPLETED, booking CONFIRMED  ──webhooks──▶ payment.succeeded, booking.confirmed
      card declined ─▶ 402, session stays PENDING           ──webhook───▶ payment.failed (retry allowed)
      no payment in 30 min ─▶ booking EXPIRED, session EXPIRED, seats released ──▶ booking.expired
      booking cancelled ─▶ open session CANCELLED / paid session REFUNDED
```
Session status: `PENDING → COMPLETED (→ REFUNDED) | EXPIRED | CANCELLED`.

## Card rules (sandbox)
- **Number:** must be one of the published test cards (see [payments policy](../policies/payments-and-currency.md)); anything else is declined.
- **Expiry:** `MMYY` or `MM/YY`, in the future.
- **CVV:** 4 digits for American Express, 3 for other cards.
- **Cardholder name:** required.
- Every attempt is logged (`payment_attempts`). Only the brand, the last 4 digits and the holder name are stored.

## Currency
A booking is priced in USD (`base_amount`) and charged in the requested `currency` at the sandbox rate. The session
stores `amount`, `currency` and `exchange_rate`. See [13 · Currency](13-currency.md).

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/bookings` | guest or `bookings:write` | Hold + session. Options: `currency`, `client_reference_id`, `metadata`, `success_url`, `cancel_url` |
| POST | `/api/bookings/{id}/payment-session` | owner, admin, or `last_name` | New link for a PENDING booking |
| GET | `/api/payment-sessions/{session_id}` | public (the secret is in the URL) | Data for the hosted page |
| POST | `/api/payment-sessions/{session_id}/pay` | public | Charge a card → 200, or 402 if declined, or 409 if not payable |
| GET | `/api/payments`, `/api/payments/{id}`, `/api/payments/{id}/attempts` | `bookings:read` (owner / admin) | Back-office views |
| POST / GET / DELETE | `/api/admin/webhooks`, `GET /api/admin/webhooks/deliveries` | `admin` | Subscriptions and the delivery log |

The hosted page URL is `{PUBLIC_UI_URL}/pay/{session_id}`. After a successful payment it redirects to `success_url`
with `session_id`, `pnr` and `status=COMPLETED` appended.

## Configuration
`BOOKING_HOLD_MINUTES` (30), `PUBLIC_UI_URL` (http://localhost:5173).

## Code
`services/payment_service.py` (sessions, cards), `services/checkout_service.py` (pay + confirm + events),
`services/webhook_service.py` (subscriptions, HMAC signing, deliveries), and
`booking_service.create_booking / new_payment_session / confirm_paid / expire_holds`.
