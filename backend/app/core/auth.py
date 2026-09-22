"""
Authentication utilities for QueryNest.

Handles:
- Password hashing
- Password verification
- JWT creation
- JWT decoding
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY is not set in the environment.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)


def hash_password(password: str) -> str:
    """
    Hash a user's password using bcrypt.
    """
    password_bytes = password.encode("utf-8")

    # bcrypt only accepts passwords up to 72 bytes.
    # Enforce this explicitly with a clear error.
    if len(password_bytes) > 72:
        raise ValueError(
            "Password cannot be longer than 72 UTF-8 bytes."
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    """
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    'subject' should normally be the authenticated user's ID.
    """
    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Returns the payload if valid, otherwise None.
    """
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except JWTError:
        return None


def get_token_subject(token: str) -> str | None:
    """
    Extract the user ID from the JWT 'sub' claim.
    """
    payload = decode_access_token(token)

    if not payload:
        return None

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        return None

    return subject