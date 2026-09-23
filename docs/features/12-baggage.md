# 12 · Baggage allowances

## Model
The allowance depends on the **route type**, the **cabin** and the **passenger type**. A journey is domestic only if
every segment is domestic. Each allowance has `checked_pieces`, `checked_kg` (the total), `cabin_pieces`, `cabin_kg`
(per piece), `personal_item`, `tier_bonus_kg` and `notes`.

- Adults and children get the same allowance.
- Infants get a 5 kg cabin bag only, plus a free stroller or car seat.
- Members get their tier's bonus added to checked baggage: Silver +5 kg, Gold +15 kg. This applies to adults and children on bookings owned by the member.

The full table is in the [baggage policy](../policies/baggage.md). For example:
- domestic Economy: 1 × 15 kg checked, 1 × 7 kg cabin, plus a personal item;
- international Economy: 1 × 25 kg checked.

## Where it appears
- **Itinerary search:** `available_classes[].baggage` for ADULT, CHILD and INFANT, plus a `domestic` flag. Direct flight search also includes it.
- **Booking view:** `passengers[].baggage` per journey (OUTBOUND / RETURN), including the tier bonus.
- **Boarding pass:** `baggage`.
- **Public table:** `GET /api/baggage/allowances`, also shown on the Help → Baggage page.

## Code
`services/baggage_service.py` (the `DOMESTIC` and `INTERNATIONAL` tables, and `INFANT_CABIN_KG`).
