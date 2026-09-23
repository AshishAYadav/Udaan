"""Password hashing (PBKDF2, stdlib) and JWT access tokens."""
import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt

from app.config import settings
from app.utils.timeutils import utcnow

PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def create_access_token(user: dict, scopes: list[str]) -> tuple[str, int]:
    """Return (token, expires_in_seconds). Claims follow RFC 9068 naming (sub, scope)."""
    now = utcnow()
    lifetime = timedelta(minutes=settings.access_token_minutes)
    claims = {
        "iss": settings.jwt_issuer,
        "sub": user["user_id"],
        "iat": now,
        "exp": now + lifetime,
        "scope": " ".join(scopes),
        "username": user["username"],
        "name": f"{user['first_name']} {user['last_name']}",
        "role": user["role"],
        "tier": user.get("tier_id"),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError when the token is invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], issuer=settings.jwt_issuer)
