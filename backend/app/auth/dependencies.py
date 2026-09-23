"""FastAPI dependencies: bearer-token authentication and scope checks."""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from app.auth.scopes import SCOPES
from app.auth.security import decode_access_token
from app.db.database import repositories as db
from app.models.enums import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", scopes=SCOPES)
# Same scheme without auto-401, for endpoints that also serve guests.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", scopes=SCOPES, auto_error=False)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""

    user_id: str
    username: str
    role: Role
    tier_id: str | None
    scopes: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def has(self, scope: str) -> bool:
        return scope in self.scopes

    def owns(self, user_id: str | None) -> bool:
        return self.is_admin or user_id == self.user_id


def _unauthorized(detail: str, security_scopes: SecurityScopes) -> HTTPException:
    challenge = f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": challenge})


def get_principal(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)) -> Principal:
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Access token has expired.", security_scopes)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid access token.", security_scopes)

    user = db.users.get(claims["sub"])
    if not user:
        raise _unauthorized("User no longer exists.", security_scopes)

    granted = frozenset(claims.get("scope", "").split())
    missing = [s for s in security_scopes.scopes if s not in granted]
    if missing:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Token is missing required scope(s): {', '.join(missing)}.",
            headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
        )
    return Principal(user["user_id"], user["username"], Role(user["role"]), user.get("tier_id"), granted)


def require(*scopes: str):
    """Dependency requiring a valid token carrying all given scopes."""
    return Security(get_principal, scopes=list(scopes))


def get_optional_principal(
    security_scopes: SecurityScopes, token: str | None = Depends(optional_oauth2_scheme)
) -> Principal | None:
    """None for guests; a presented token must still be valid and carry the scopes."""
    return get_principal(security_scopes, token) if token else None


def optional(*scopes: str):
    """Dependency for endpoints open to guests: validates a token only when one is sent."""
    return Security(get_optional_principal, scopes=list(scopes))


def owns(actor: Principal | None, user_id: str | None) -> bool:
    """True when the caller is an admin or the owner of a record. Guests own nothing."""
    return actor is not None and actor.owns(user_id)
