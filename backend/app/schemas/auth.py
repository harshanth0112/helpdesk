"""
Auth Pydantic schemas — request/response contracts for all authentication endpoints.

Design decisions:
- RegisterRequest omits 'role': public registration always produces 'employee'.
- Passwords require >= 8 chars + at least one letter and one digit.
- UserMeResponse never exposes password_hash, failed_login_attempts, or locked_until.
"""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _validate_password_strength(password: str) -> str:
    """Enforce minimum security rules on a plain-text password."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    return password


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Public registration payload. Role is intentionally absent."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name fields must not be blank.")
        return v.strip()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Token responses
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access_token expires


# ---------------------------------------------------------------------------
# Refresh / Logout
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Password management
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current password.")
        return self


# ---------------------------------------------------------------------------
# /me response — safe user representation
# ---------------------------------------------------------------------------

class UserMeResponse(BaseModel):
    """Public user profile — deliberately omits all security-sensitive columns."""

    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    approval_status: str = "approved"
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterResponse(UserMeResponse):
    """Returned on public registration — no tokens issued."""

    message: str = (
        "Your registration has been submitted successfully. "
        "Please wait for administrator approval before logging in."
    )
