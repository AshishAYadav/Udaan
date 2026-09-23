# Payment links, webhooks and AI agents (MCP)

This guide shows how to connect an LLM agent, for example through MCP tools, to Udaan Airlines. The agent can search
and book, send the traveller a **payment link**, and learn about the payment **asynchronously**.

## Is this how production systems do it?

Yes. This is the pattern Stripe Checkout / Payment Links, Adyen Pay by Link and Razorpay Payment Links all use:

1. The server creates a **payment session** with a hosted-page URL. The agent never touches card data, which keeps it out of PCI scope.
2. The payer completes the payment in a browser.
3. The payment provider notifies your backend through a **signed webhook**. The backend resumes the workflow or
   conversation. As a fallback, it can poll the status.

An agent should **never** collect card numbers in chat. It should only hand out links.

## Flow

```
User ──chat──▶ Agent (LLM)
                  │ tool: search_itineraries      → GET  /api/itineraries/search
                  │ tool: create_passengers       → POST /api/passengers
                  │ tool: hold_booking            → POST /api/bookings   {…, client_reference_id: "<conversation id>"}
                  │                                  ◀─ { booking: {pnr, status: PENDING}, payment: {payment_url, expires_at} }
                  │ reply: "Pay here within 30 min: <payment_url>"
User ──browser──▶ /pay/{session_id}  (hosted UdaanPay page)  ─▶ POST /api/payment-sessions/{id}/pay
                                                         │
Udaan ──webhook──▶ Your agent backend  (payment.succeeded, booking.confirmed | payment.failed | booking.expired)
                  │ verify signature, look up the conversation by data.client_reference_id
                  └▶ Agent posts: "Paid! Your booking ZJDTKL is confirmed."
```

## Suggested MCP tools

The tools are thin wrappers around these endpoints. Use a service account (an admin or a dedicated user), or act as a guest.

| Tool | Endpoint | Notes |
|---|---|---|
| `search_itineraries(origin, destination, date, return_date?, adults, children, infants, cabin?)` | `GET /api/itineraries/search` | Returns `flight_ids`, prices by passenger type and baggage |
| `create_passenger(first, last, dob, gender)` | `POST /api/passengers` | One call per traveller |
| `hold_booking(outbound_flight_ids, return_flight_ids, class_id, passenger_ids, currency?, client_reference_id)` | `POST /api/bookings` | Returns the PNR and `payment.payment_url` |
| `get_payment_link(booking_id, last_name, currency?)` | `POST /api/bookings/{id}/payment-session?last_name=` | A fresh link for a PENDING booking |
| `get_booking(pnr, last_name)` | `GET /api/bookings/pnr/{pnr}?last_name=` | Status, flights, check-in and baggage |
| `cancel_booking(booking_id, last_name)` | `POST /api/bookings/{id}/cancel?last_name=` | Refunds paid bookings |
| `checkin(pnr, last_name, flight_ids?, passenger_ids?)` | `POST /api/checkins` | Returns boarding passes |
| `policy_lookup(topic)` | `GET /api/policies/{slug}` | Or use RAG over `docs/policies` |

Tips for the tool descriptions: tell the model that a booking is **not confirmed until the webhook arrives**, and
that holds expire in 30 minutes.

## Webhooks

**Subscribe once as an admin:**
```bash
curl -X POST $API/admin/webhooks -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"url":"https://agent.example.com/hooks/udaan","events":["payment.succeeded","payment.failed","booking.confirmed","booking.expired"]}'
# → {"webhook_id":"WH001","secret":"whsec_…", …}   keep the secret
```

**Event payload:**
```json
{
  "id": "evt_4f…", "type": "payment.succeeded", "created": "2026-09-24T10:12:03+00:00",
  "data": {
    "booking_id": "BK001", "pnr": "ZJDTKL", "status": "CONFIRMED", "user_id": null,
    "amount": 206996.5, "currency": "INR", "payment_id": "PAY001", "payment_status": "COMPLETED",
    "client_reference_id": "chat-42", "metadata": {"channel": "whatsapp"}
  }
}
```

**Events:**

| Event | When |
|---|---|
| `booking.held` | Booking held, link created |
| `payment.succeeded` | Card charged |
| `booking.confirmed` | Booking confirmed |
| `payment.failed` | Card declined (includes a `reason`; the user can retry) |
| `booking.expired` | Hold lapsed, seats released |
| `booking.cancelled` | Booking cancelled |

**Verify the signature.** Always verify it, and reject requests whose timestamp is more than 5 minutes old:
```python
import hmac, hashlib, time
def verify(secret: str, header: str, raw_body: bytes, tolerance=300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    if abs(time.time() - int(parts["t"])) > tolerance:
        return False
    expected = hmac.new(secret.encode(), f"{parts['t']}.".encode() + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts["v1"])
```

**Delivery log:** `GET /api/admin/webhooks/deliveries` (admin) shows the status code or error for each attempt.

## Production hardening checklist

This service is a sandbox. Before a real deployment:

- **Delivery:** add webhook **retries with backoff** and an outbox table, so events survive restarts; delivery is fire-and-forget today.
- **Idempotency:** add **idempotency keys** on `POST /bookings`, and deduplicate events by `event.id` on the receiver.
- **Payment provider:** replace the test-card check with a real PSP (Stripe, Adyen, Razorpay). Keep this API's shape
  (`payment_url`, webhooks) and forward the provider's webhooks into `confirm_paid`.
- **Transport:** serve everything over HTTPS, set `PUBLIC_UI_URL` to the public domain, and rotate webhook secrets.
- **Agent authorisation:** give agents **narrow OAuth scopes**. For example, a service token with `bookings:write` only, no admin.
