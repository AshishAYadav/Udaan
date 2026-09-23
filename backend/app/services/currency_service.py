"""Point-of-sale currencies.

Fares are filed in the base currency (USD). A booking can be priced and paid in
a local currency using sandbox reference rates. The currency is suggested from
the caller's country: a CDN geo header such as `CF-IPCountry`, or the region in
`Accept-Language`.
"""
from app.config import settings
from app.utils.errors import BadRequestError

# Units of currency per 1 USD (static sandbox reference rates).
RATES: dict[str, float] = {
    "USD": 1.0,
    "INR": 83.50,
    "AED": 3.6725,
    "GBP": 0.79,
    "EUR": 0.92,
    "SGD": 1.35,
    "JPY": 150.0,
    "AUD": 1.52,
    "QAR": 3.64,
}
ZERO_DECIMAL = {"JPY"}
NAMES = {
    "USD": "US Dollar", "INR": "Indian Rupee", "AED": "UAE Dirham", "GBP": "British Pound", "EUR": "Euro",
    "SGD": "Singapore Dollar", "JPY": "Japanese Yen", "AUD": "Australian Dollar", "QAR": "Qatari Riyal",
}
COUNTRY_CURRENCY = {
    "US": "USD", "IN": "INR", "AE": "AED", "GB": "GBP", "FR": "EUR", "DE": "EUR", "IE": "EUR", "IT": "EUR",
    "ES": "EUR", "NL": "EUR", "SG": "SGD", "JP": "JPY", "AU": "AUD", "QA": "QAR",
}


def list_currencies() -> list[dict]:
    return [{"code": c, "name": NAMES[c], "rate": r, "decimals": 0 if c in ZERO_DECIMAL else 2} for c, r in RATES.items()]


def validate(currency: str | None) -> str:
    code = (currency or settings.currency).upper()
    if code not in RATES:
        raise BadRequestError(f"Unsupported currency {code}. Supported: {', '.join(RATES)}.")
    return code


def convert(amount: float, currency: str) -> float:
    """Convert an amount in the base currency."""
    value = amount * RATES[validate(currency)]
    return round(value) if currency in ZERO_DECIMAL else round(value, 2)


def detect(country_header: str | None, accept_language: str | None) -> dict:
    country = (country_header or "").strip().upper() or None
    if not country and accept_language:
        # e.g. "en-IN,en;q=0.9" -> IN
        first = accept_language.split(",")[0].strip()
        if "-" in first:
            country = first.split("-")[1][:2].upper()
    currency = COUNTRY_CURRENCY.get(country or "", settings.currency)
    return {"country": country, "currency": currency, "source": "geo-header" if country_header else "accept-language" if country else "default"}
