from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.common import error_responses
from app.auth.dependencies import Principal, require
from app.schemas.auth import Profile, RegisterRequest, Token
from app.schemas.reference import UserDetail
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token, responses=error_responses(400, auth=False), summary="Get an access token",
             description="OAuth2 **password grant** (RFC 6749 §4.3). Send `username`, `password` and optionally "
                         "`scope` (space-separated) as form data. Returns a signed JWT bearer token.\n\n"
                         "Granted scopes depend on the user: customers get booking scopes plus one `ssr:<TYPE>` "
                         "scope per SSR their tier allows; admins get every scope. If you request no scopes, you get "
                         "every scope you're allowed. If you request some, you get the ones you're allowed.")
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return auth_service.login(form.username, form.password, form.scopes)


@router.post("/register", response_model=UserDetail, status_code=status.HTTP_201_CREATED,
             responses=error_responses(400, 409, auth=False), summary="Register a customer",
             description="Creates a customer account in the Bronze tier. Then call `/auth/token` to log in.")
def register(payload: RegisterRequest):
    return auth_service.register(payload)


@router.get("/me", response_model=Profile, responses=error_responses(), summary="Current user",
            description="The authenticated user, tier, the scopes in this token and every scope the user may request.")
def me(actor: Principal = require("profile")):
    return auth_service.profile(actor.user_id, actor.scopes)
