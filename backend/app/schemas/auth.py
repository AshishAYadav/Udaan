from pydantic import BaseModel, Field

from app.schemas.reference import UserDetail


class Token(BaseModel):
    access_token: str
    token_type: str = Field(examples=["bearer"])
    expires_in: int = Field(description="Lifetime in seconds")
    scope: str = Field(description="Space-separated granted scopes")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, examples=["jane.doe"])
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str
    phone: str = ""


class Profile(UserDetail):
    scopes: list[str] = Field(description="Scopes in the presented token")
    allowed_scopes: list[str] = Field(description="Scopes this user may be granted")
