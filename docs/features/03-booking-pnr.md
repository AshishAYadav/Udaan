# 03 · Booking & PNR retrieval

## Purpose
Confirm a one-way or round-trip reservation against a completed payment, reserve seats on every segment and issue a
unique **PNR**. Retrieve itineraries the way airlines do, with the PNR (or booking ID) and a passenger's last name.

## Booking rules
Creating a booking (`POST /api/bookings`) **holds** it. All of the following must hold:
- the booker is valid: guests book without an account (`user_id = null`), customers always book for themselves, and admins may pass `user_id`;
- every flight is bookable (SCHEDULED or DELAYED, not departed), and the connections and trip order are valid (see [02](02-flight-search-itineraries.md));
- the cabin exists on every segment with enough seats; infants don't take a seat;
- the party is valid (see [06](06-passengers.md)), and every passenger belongs to the booking user or is a guest passenger not on another live booking;
- no passenger is already on a held or active booking for any of the same flights.

On success:
- seats are reserved on every segment;
- a 6-character PNR is generated (it never uses `0 O 1 I`, and is unique);
- the booking is **PENDING** with `hold_expires_at` 30 minutes later;
- a hosted payment session is opened (see [04](04-payments.md)).

Paying confirms the booking. **No ticket is issued yet**; tickets are issued at check-in.

Statuses: `PENDING` (held) → `CONFIRMED` → `CHANGED` (after a journey change). A booking can also end as `CANCELLED`
or `EXPIRED` (hold lapsed; seats released).

## Data model
```json
{
  "booking_id": "BK001", "pnr": "65CMD3", "user_id": "USR002", "trip_type": "ROUND_TRIP",
  "segments": [
    {"segment_no": 1, "flight_id": "FLT008", "direction": "OUTBOUND"},
    {"segment_no": 2, "flight_id": "FLT009", "direction": "OUTBOUND"},
    {"segment_no": 3, "flight_id": "FLT021", "direction": "RETURN"},
    {"segment_no": 4, "flight_id": "FLT025", "direction": "RETURN"}
  ],
  "class_id": "ECONOMY", "passenger_ids": ["PAX001", "PAX002"], "payment_id": "PAY001",
  "base_amount": 2345.0, "total_amount": 195807.5, "currency": "INR",
  "status": "CONFIRMED", "hold_expires_at": null
}
```

## Retrieval (PNR + last name)

| Request | Who | Rule |
|---|---|---|
| `GET /api/bookings/pnr/{pnr}?last_name=` | anyone, including guests | `last_name` is **mandatory** and must match a passenger |
| `GET /api/bookings/{booking_id}?last_name=` | anyone, including guests | owners and admins may omit `last_name`; everyone else must supply a matching one |
| `GET /api/bookings` | `bookings:read` | the caller's own bookings, newest first. Admins see all bookings, including guest bookings, and can filter by `user_id`, `status` or `pnr` |

A wrong PNR and a wrong last name get the same **404**, so the response doesn't reveal whether a PNR exists. The
last-name match ignores case and surrounding spaces.

The **booking view** returns the header, `passengers`, `segments[]` (each with its flight and per-passenger check-in,
seat and ticket status), payment and SSRs. The UI shows it on the confirmation, My Booking and check-in screens.

## Other endpoints
`PUT /api/bookings/{id}` (contact details) and `GET /api/bookings/{id}/history` need the owner, an admin, or `last_name`.

**Admin delete:** `DELETE /api/bookings/{id}` (`admin`) permanently removes a booking with its check-ins, tickets,
SSRs and history. An active booking's seats are released and its payment refunded first; the payment record is kept
for audit. Use cancel instead to keep the PNR on record. Change and cancel are covered in
[05](05-booking-change-cancellation.md).

## Code
`services/booking_service.py`: `create_booking`, `find_by_pnr`, `get_booking`, `build_view`.
