"""Login (token issuance), self-registration and profile."""
import re

from app.auth.scopes import allowed_scopes, grant
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.database import next_id
from app.db.database import repositories as db
from app.models.enums import Role
from app.services import reference_service as ref
from app.utils.errors import BadRequestError, ConflictError
from app.utils.timeutils import now_iso

DEFAULT_TIER = "BRONZE"


def _tier(user: dict) -> dict | None:
    return db.tiers.get(user["tier_id"]) if user.get("tier_id") else None


def login(username: str, password: str, requested_scopes: list[str]) -> dict:
    user = db.users.find_one(username=username.strip().lower())
    if not user or not verify_password(password, user["password_hash"]):
        raise BadRequestError("Incorrect username or password.")
    scopes = grant(user, _tier(user), requested_scopes)
    token, expires_in = create_access_token(user, scopes)
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in, "scope": " ".join(scopes)}


def register(data) -> dict:
    username = data.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
        raise BadRequestError("Username must be 3-30 characters: letters, digits, dot, dash or underscore.")
    if db.users.find_one(username=username):
        raise ConflictError(f"Username {username} is already taken.")
    user = {
        "user_id": next_id("USR"),
        "username": username,
        "password_hash": hash_password(data.password),
        "role": Role.CUSTOMER.value,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "phone": data.phone,
        "tier_id": DEFAULT_TIER,
        "created_at": now_iso(),
    }
    db.users.insert(user)
    return ref.get_user(user["user_id"])


def profile(user_id: str, token_scopes: frozenset[str]) -> dict:
    user = ref.get_user(user_id)
    return {**user, "scopes": sorted(token_scopes), "allowed_scopes": allowed_scopes(user, user["tier"])}
