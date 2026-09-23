"""OAuth2 scopes and how they are granted.

Customers receive base scopes plus one `ssr:<TYPE>` scope per SSR their tier is
eligible for, so a token cannot request services the user is not entitled to.
Admins receive every scope.
"""
from app.models.enums import Role, SSRType

SSR_SCOPES = {f"ssr:{t.value}": f"Request the {t.value.replace('_', ' ').lower()} special service" for t in SSRType}

SCOPES: dict[str, str] = {
    "profile": "Read your own profile",
    "passengers:write": "Create and modify your passengers",
    "bookings:read": "Read your bookings and itineraries",
    "bookings:write": "Create, change and cancel your bookings",
    "payments:write": "Create and complete mock payments",
    "checkin:write": "Check in and manage seats",
    "ssr:read": "View special service requests and eligibility",
    "ssr:write": "Create and cancel special service requests (with the matching ssr:<TYPE> scope)",
    **SSR_SCOPES,
    "flights:write": "Create and modify flight schedules (admin)",
    "tickets:write": "Issue and cancel tickets manually (admin)",
    "admin": "Read all records and use administrative endpoints (admin)",
}

CUSTOMER_SCOPES = [
    "profile",
    "passengers:write",
    "bookings:read",
    "bookings:write",
    "payments:write",
    "checkin:write",
    "ssr:read",
]


def allowed_scopes(user: dict, tier: dict | None) -> list[str]:
    if user["role"] == Role.ADMIN:
        return list(SCOPES)
    scopes = list(CUSTOMER_SCOPES)
    eligible = (tier or {}).get("eligible_ssrs", [])
    if eligible:
        scopes += ["ssr:write", *(f"ssr:{t}" for t in eligible)]
    return scopes


def grant(user: dict, tier: dict | None, requested: list[str]) -> list[str]:
    """Scopes to put in a token: the requested subset of allowed scopes, or all allowed if none requested."""
    allowed = allowed_scopes(user, tier)
    return [s for s in allowed if s in requested] if requested else allowed
