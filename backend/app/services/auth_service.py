"""
app/services/auth_service.py — Business logic for all authentication flows.

This module is the single source of truth for:
  - User registration
  - User authentication (with brute-force lockout)
  - JWT + refresh-token pair creation
  - Refresh-token rotation with reuse detection
  - Refresh-token revocation (logout)
  - Password-reset initiation and completion

Design decisions:
  - MAX_FAILED_ATTEMPTS = 5 before 15-minute lockout.
  - Refresh tokens are 256-bit random values; only their SHA-256 hash is
    persisted.  The raw token is returned to the client and immediately
    discarded from server memory.
  - Reuse detection: if a *revoked* refresh token is presented, all tokens
    for that user are revoked immediately (token theft assumed).
  - Password reset tokens are single-use and expire in 30 minutes.
  - For this phase, the "forgot password" endpoint returns the raw reset
    token in the API response (to allow testing without an email server).
    In production, replace with an email dispatch.
  - Generic error messages are used throughout to prevent user enumeration.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    generate_jwt_access_token,
    generate_secure_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, ResetPasswordRequest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FAILED_ATTEMPTS: int = 5
LOCKOUT_MINUTES: int = 15


class AccountStatusError(Exception):
    """Raised when credentials are valid but account is pending, rejected, or suspended."""

    def __init__(self, message: str, audit_action: str, user_id: int):
        super().__init__(message)
        self.audit_action = audit_action
        self.user_id = user_id


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(db: Session, data: RegisterRequest) -> User:
    """
    Create a new *employee* account with approval_status='pending'.

    Raises ``ValueError`` if the email address is already registered.
    Role is always set to 'employee' regardless of any client input.
    """
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise ValueError("An account with that email address already exists.")

    user = User(
        email=data.email.lower(),
        password_hash=get_password_hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role="employee",           # public registration always creates employee
        phone=data.phone,
        department=data.department,
        is_active=True,
        approval_status="pending",
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Authentication (with brute-force protection & approval check)
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verify credentials, check approval/active status, and return the authenticated User.

    Raises:
        ValueError — on invalid credentials or account lockout.
        AccountStatusError — when password is valid but account is pending, rejected, or suspended.
    """
    _GENERIC_MSG = "Invalid email or password."

    user: User | None = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        # Perform a dummy hash to maintain consistent timing
        verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
        raise ValueError(_GENERIC_MSG)

    # Check lockout
    now = datetime.now(timezone.utc)
    if user.locked_until:
        locked_until_aware = user.locked_until
        if locked_until_aware.tzinfo is None:
            locked_until_aware = locked_until_aware.replace(tzinfo=timezone.utc)
        if locked_until_aware > now:
            raise ValueError(
                f"Account is temporarily locked. Try again after "
                f"{locked_until_aware.strftime('%H:%M UTC')}."
            )
        else:
            # Lockout expired — reset counters
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # Verify password BEFORE checking approval/active status to prevent unauthenticated enumeration
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        raise ValueError(_GENERIC_MSG)

    if user.approval_status == "pending":
        raise AccountStatusError(
            "Your account is awaiting administrator approval.",
            audit_action="login_blocked_pending_approval",
            user_id=user.id,
        )

    if user.approval_status == "rejected":
        raise AccountStatusError(
            "Your registration was not approved. Contact the administrator.",
            audit_action="login_blocked_rejected",
            user_id=user.id,
        )

    if user.approval_status == "suspended" or not user.is_active:
        raise AccountStatusError(
            "Your account has been suspended. Contact the administrator.",
            audit_action="login_blocked_suspended",
            user_id=user.id,
        )

    # Successful authentication — reset failure counters
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Token pair creation
# ---------------------------------------------------------------------------

def create_token_pair(
    db: Session,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """
    Generate a JWT access token + opaque refresh token for *user*.

    The raw refresh token is returned (to be sent to the client); only
    its SHA-256 hash is persisted in the database.
    """
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = generate_jwt_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )

    raw_refresh = generate_secure_token()
    hashed_refresh = hash_token(raw_refresh)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=refresh_expires_at,
        is_revoked=False,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(db_refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
    }


# ---------------------------------------------------------------------------
# Refresh-token rotation
# ---------------------------------------------------------------------------

def rotate_refresh_token(
    db: Session,
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """
    Validate *raw_token*, revoke it, and issue a new token pair.

    Reuse detection: if the presented token is already revoked, **all**
    refresh tokens for that user are revoked immediately (token theft assumed).

    Raises ``ValueError`` on any failure (generic message).
    """
    _GENERIC_MSG = "Invalid or expired refresh token."

    token_hash = hash_token(raw_token)
    db_token: RefreshToken | None = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )

    if db_token is None:
        raise ValueError(_GENERIC_MSG)

    # Reuse detection — already revoked token presented
    if db_token.is_revoked:
        # Revoke ALL tokens for this user (token theft response)
        db.query(RefreshToken).filter(
            RefreshToken.user_id == db_token.user_id,
            RefreshToken.is_revoked.is_(False),
        ).update(
            {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
        db.commit()
        raise ValueError(_GENERIC_MSG)

    # Check expiry
    now = datetime.now(timezone.utc)
    expires_at_aware = db_token.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)
    if expires_at_aware < now:
        raise ValueError(_GENERIC_MSG)

    # Revoke the consumed token
    db_token.is_revoked = True
    db_token.revoked_at = now
    db.commit()

    # Load user and issue a new pair
    user: User | None = db.get(User, db_token.user_id)
    if user is None or not user.is_active or user.approval_status != "approved":
        raise ValueError(_GENERIC_MSG)

    return create_token_pair(db, user, ip_address=ip_address, user_agent=user_agent)


# ---------------------------------------------------------------------------
# Logout / revocation
# ---------------------------------------------------------------------------

def revoke_refresh_token(db: Session, raw_token: str) -> None:
    """
    Mark a specific refresh token as revoked (logout).

    Silently succeeds even if the token is not found or already revoked,
    so logout is always idempotent from the client's perspective.
    """
    token_hash = hash_token(raw_token)
    db_token: RefreshToken | None = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )
    if db_token and not db_token.is_revoked:
        db_token.is_revoked = True
        db_token.revoked_at = datetime.now(timezone.utc)
        db.commit()


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def initiate_password_reset(db: Session, email: str) -> str | None:
    """
    Generate a password-reset token for *email*.

    Returns the **raw** token string so the caller can dispatch it via email.
    Returns ``None`` if the email is not registered (caller must NOT reveal
    this difference to the client — always return a generic success message).

    For Phase 4 testing the raw token is also included in the API response.
    Replace with email dispatch in production.
    """
    user: User | None = db.query(User).filter(User.email == email.lower()).first()
    if user is None or not user.is_active:
        return None

    raw_token = generate_secure_token()
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    db_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hashed,
        expires_at=expires_at,
        is_used=False,
    )
    db.add(db_token)
    db.commit()
    return raw_token


def complete_password_reset(db: Session, raw_token: str, new_password: str) -> None:
    """
    Validate *raw_token* and update the user's password.

    Raises ``ValueError`` on any failure (generic to prevent enumeration).
    """
    _GENERIC_MSG = "Invalid or expired password reset token."

    token_hash = hash_token(raw_token)
    db_token: PasswordResetToken | None = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if db_token is None:
        raise ValueError(_GENERIC_MSG)
    if db_token.is_used:
        raise ValueError(_GENERIC_MSG)

    now = datetime.now(timezone.utc)
    expires_at_aware = db_token.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)
    if expires_at_aware < now:
        raise ValueError(_GENERIC_MSG)

    user: User | None = db.get(User, db_token.user_id)
    if user is None or not user.is_active:
        raise ValueError(_GENERIC_MSG)

    user.password_hash = get_password_hash(new_password)
    db_token.is_used = True
    db_token.used_at = now
    db.commit()
