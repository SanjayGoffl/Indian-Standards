"""
Authentication API for QueryNest.

Endpoints:
- POST /auth/register
- POST /auth/login
- GET  /auth/me
- POST /auth/logout
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.database import get_db
from app.core.models import User
from app.dependencies.auth import get_current_user
from app.models.auth_models import (
    AuthTokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)


# Authentication routes are grouped under /auth.
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _user_to_profile(
    user: User,
) -> UserProfileResponse:
    """
    Convert a database user into the public API profile.
    """
    return UserProfileResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        role=user.role or "User",
        avatar=user.avatar,
        created_at=(
            user.created_at.isoformat()
            if user.created_at
            else datetime.now(
                timezone.utc
            ).isoformat()
        ),
    )


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    """
    Create a new user account and sign the user in.
    """
    email = payload.email.strip().lower()
    full_name = payload.full_name.strip()

    # Normalize and validate the supplied values.
    if not full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name cannot be empty.",
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address cannot be empty.",
        )

    # Prevent duplicate accounts.
    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Store only the password hash.
    password_hash = hash_password(
        payload.password
    )

    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role="User",
        avatar=None,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Put the database user ID into the JWT.
    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "email": user.email,
        },
    )

    return AuthTokenResponse(
        success=True,
        token=token,
        token_type="bearer",
        user=_user_to_profile(user),
        message="Account created successfully!",
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    """
    Authenticate an existing user.
    """
    email = payload.email.strip().lower()

    # Find the account by normalized email.
    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    # Use one generic error for unknown users and bad passwords.
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked. Please contact an administrator.",
        )

    # Issue a fresh access token after successful login.
    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "email": user.email,
        },
    )

    return AuthTokenResponse(
        success=True,
        token=token,
        token_type="bearer",
        user=_user_to_profile(user),
        message="Welcome back!",
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
) -> UserProfileResponse:
    """
    Return the currently authenticated user's profile.
    """
    return _user_to_profile(
        current_user
    )


@router.post(
    "/logout",
)
def logout(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Complete the logout request.

    JWT access tokens are stateless, so the frontend removes
    the token immediately. The short token lifetime limits
    the lifetime of a token that has already been issued.
    """
    return {
        "success": True,
        "message": "Successfully logged out.",
        "user_id": str(
            current_user.id
        ),
    }