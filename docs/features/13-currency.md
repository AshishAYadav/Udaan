# 13 · Currency

- **Base currency:** fares are filed in **USD**.
- **Supported currencies:** USD, INR, AED, GBP, EUR, SGD, JPY, AUD, QAR, at static sandbox reference rates. JPY has no decimals.
- **Detection in the UI:** the browser region (`navigator.language`, e.g. `en-IN` → INR), then the time zone (e.g.
  `Asia/Dubai` → AED), then USD. The user can override it with the navbar selector, and the choice is remembered in
  `localStorage`. Prices are converted for display.
- **Detection in the API:** `GET /api/currencies/detect` reads a CDN geo-IP header (`CF-IPCountry`, `X-Country-Code`)
  first, then `Accept-Language`. In production, put the app behind a CDN or proxy that adds a geo header. Doing real
  IP geolocation in-process needs a GeoIP database such as MaxMind.
- **Charging:** `POST /api/bookings` takes `currency`. The booking and payment store `amount` in that currency,
  plus `base_amount` (USD) and `exchange_rate`. A new payment link can switch currency. Refunds use the paid currency.
- **Endpoints:** `GET /api/currencies`, `GET /api/currencies/detect`.
- **Code:** `services/currency_service.py`, `frontend/src/hooks/useCurrency.jsx`.
