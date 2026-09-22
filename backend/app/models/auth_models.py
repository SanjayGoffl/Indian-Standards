from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
    )

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )

    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="User's password",
    )


class UserLoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User's password",
    )


class UserProfileResponse(BaseModel):
    """Public user profile returned by authentication endpoints."""

    id: str
    full_name: str
    email: EmailStr
    role: str = "User"
    avatar: str | None = None
    created_at: str


class AuthTokenResponse(BaseModel):
    """Authentication response containing JWT token and user profile."""

    success: bool = True
    token: str
    token_type: str = "bearer"
    user: UserProfileResponse
    message: str = "Authentication successful"