# 06 · Passengers

## Rules
- The **type is derived from date of birth**: under 2 → `INFANT`, under 12 → `CHILD`, otherwise `ADULT`. If
  `passenger_type` is supplied it must match; otherwise the request fails with 400. For bookings, the type is worked
  out again from the age on the first departure date.
- A party has **at least one adult**; unaccompanied minors aren't supported. There can be **no more infants than
  adults**, and each adult accompanies at most one infant. An infant may name `accompanying_adult_id`, who must be an
  adult in the same booking.
- Infants travel on an adult's lap: they take no seat and get seat `INF` at check-in.
- A booking can have at most 9 seated passengers.
- A passenger on an active booking can't be deleted, and can't have a date-of-birth change that alters their type.

## Ownership
A passenger belongs to the user who created it. Customers only see their own passengers, and a customer can't book
passengers that belong to someone else (403). Admins may create passengers for any `user_id`.

## API
`GET/POST /api/passengers`, `GET/PUT/DELETE /api/passengers/{id}`. Reading needs `bookings:read`; writing needs
`passengers:write`.

## Configuration
`infant_max_age` (2), `child_max_age` (12), `child_fare_factor` (0.75), `infant_fare_factor` (0.10), `max_seats_per_booking` (9).
