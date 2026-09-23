# Udaan Airlines policy documents

Customer-facing policies. They are written to be:

- **the single source** shown on the website Help page (`GET /api/policies`, `GET /api/policies/{slug}`);
- **ready for retrieval (RAG)** by an AI booking assistant. Each file covers one topic, repeats the key numbers in
  full sentences, uses headings that work as chunk boundaries, and ends with question-and-answer pairs.

Numbers match the backend defaults in `backend/app/config.py`. If you change a setting there, update these files too.

| File | Topic |
|---|---|
| `booking-and-ticketing.md` | How to book, holds, PNR, guest vs member, limits |
| `fares-and-passengers.md` | Passenger types, age rules, infant and child fares, party rules |
| `baggage.md` | Checked, cabin and infant baggage by route and cabin |
| `checkin-and-boarding.md` | Check-in window, rules for infants, boarding and gate times, boarding passes |
| `flight-status.md` | What each flight status means |
| `changes-cancellations-refunds.md` | Changing flights, cancelling, refunds, expired holds |
| `payments-and-currency.md` | Hosted payment page, accepted cards, currencies, security |
| `special-services-and-membership.md` | Udaan Club tiers and special service requests (meals, lounge, …) |
