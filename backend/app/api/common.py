from app.schemas.common import ErrorResponse

_DESCRIPTIONS = {
    400: "Invalid request or business rule violation",
    401: "Missing, invalid or expired access token",
    403: "Token lacks the required scope or the resource belongs to another user",
    404: "Resource not found",
    409: "Conflict with the current state of the resource",
}


def error_responses(*codes: int, auth: bool = True) -> dict:
    """OpenAPI `responses` entries for domain errors (401/403 included for protected endpoints)."""
    codes = (*codes, 401, 403) if auth else codes
    return {code: {"model": ErrorResponse, "description": _DESCRIPTIONS[code]} for code in codes}
