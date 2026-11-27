"""
app/core/security.py — Low-level cryptographic helpers.

Responsibilities:
  - Password hashing and verification via Argon2 (through passlib).
  - JWT access-token generation and verification via python-jose.
  - Cryptographically secure raw token generation (for refresh / reset tokens).
  - SHA-256 hashing of raw tokens before database storage.

Design decisions:
  - Argon2 is the recommended algorithm from OWASP for password hashing; it is
    memory-hard and resistant to GPU/ASIC attacks.
  - JWT access tokens are short-lived (default 15 min) and signed with HS256.
  - Refresh and reset tokens are 256-bit random values (secrets.token_urlsafe(32));
    only their SHA-256 digest is stored in the database, so a database breach does
    not expose reusable tokens.
  - verify_password uses passlib's constant-time comparison under the hood,
    preventing timing-based enumeration of password hashes.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.hash import argon2

from app.config import settings


# ---------------------------------------------------------------------------
# Password hashing — Argon2
# ---------------------------------------------------------------------------

def get_password_hash(plain: str) -> str:
    """Return an Argon2 hash of *plain*.  Never store the plaintext."""
    return argon2.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Constant-time comparison of *plain* against *hashed*.
    Returns True only if the password matches.
    """
    try:
        return argon2.verify(plain, hashed)
    except Exception:
        # Any internal passlib error → treat as mismatch (safe default)
        return False


# ---------------------------------------------------------------------------
# JWT access tokens — python-jose
# ---------------------------------------------------------------------------

def generate_jwt_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Encode *data* into a signed JWT.

    The ``exp`` claim is always set; if *expires_delta* is omitted the value from
    settings is used.  The ``iat`` (issued-at) claim is added for auditability.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """
    Decode and verify *token*.  Raises ``jose.JWTError`` if the token is
    invalid, expired, or has a bad signature — callers must handle this.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Opaque token helpers — refresh tokens & password-reset tokens
# ---------------------------------------------------------------------------

def generate_secure_token() -> str:
    """
    Return a 256-bit URL-safe random token string.
    This raw value is sent to the client and NEVER stored in the database.
    """
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """
    Return the SHA-256 hex digest of *raw_token*.
    Only this digest is stored in the database.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
