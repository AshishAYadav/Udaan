# 05 · Booking change & cancellation

## Journey change
`POST /api/bookings/{id}/change` `{"direction": "OUTBOUND" | "RETURN", "new_flight_ids": [...]}`. Needs
`bookings:write`, and the caller must be the owner or an admin.

This replaces a whole journey (direct or connecting) with another itinerary between the **same airports** and in the
same cabin. Rules:
1. The booking is active (CONFIRMED or CHANGED).
2. The request is made **more than 24 hours** before the journey's first departure.
3. The new journey departs **no later than 60 days** after the original first departure (`CHANGE_WINDOW_DAYS`).
4. The new journey's connections are valid, and the whole trip still is: the return must still leave after the outbound arrives.
5. There are enough seats on every flight added. Flights kept in the journey are not re-counted.
6. Nobody is checked in on the journey. Offload them first with `PUT /api/checkins/{id}`.

Effects: seats are released on removed flights and taken on added ones. SSRs on removed flights are cancelled. The
status becomes `CHANGED`, and the history records `JOURNEY_CHANGED` with `fare_difference` (new fare minus old fare,
for information only; the sandbox doesn't collect it).

Example errors:
- *"The journey cannot be changed because departure is within 24 hours."*
- *"The new journey departs more than 60 days after the original (latest allowed departure …)."*
- *"The return journey must depart after the outbound journey arrives."*

## Cancellation
`POST /api/bookings/{id}/cancel` `{"reason": "…"}` (owner, admin, or `last_name`) is allowed for held or confirmed bookings before the first flight departs. It:
- sets the status to `CANCELLED`, keeping the booking and PNR;
- releases seats on every segment;
- sets a paid payment to `REFUNDED`, or closes an unpaid hold's open payment session;
- cancels check-ins (`NOT_CHECKED_IN`), tickets and SSRs.

## Configuration
`change_cutoff_hours` (24) and `CHANGE_WINDOW_DAYS` (60).

## Code
`booking_service.change_journey`, `booking_service.cancel_booking`.
