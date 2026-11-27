"""
app/routes/auth.py Ã¢â‚¬â€ Authentication API endpoints.

Endpoints:
  POST /api/v1/auth/register      Ã¢â‚¬â€ Public registration (employee role only)
  POST /api/v1/auth/login         Ã¢â‚¬â€ Credential exchange for token pair
  POST /api/v1/auth/refresh       Ã¢â‚¬â€ Refresh-token rotation
  POST /api/v1/auth/logout        Ã¢â‚¬â€ Revoke refresh token
  POST /api/v1/auth/forgot-password  Ã¢â‚¬â€ Initiate password reset
  POST /api/v1/auth/reset-password   Ã¢â‚¬â€ Complete password reset
  GET  /api/v1/auth/me            Ã¢â‚¬â€ Authenticated user profile

Rate limiting (SlowAPI):
  - Register:  10 requests / minute  per IP
  - Login:      5 requests / minute  per IP  (strict Ã¢â‚¬â€ brute-force mitigation)
  - Refresh:   20 requests / minute  per IP
  - Others: no explicit limit (authenticated or low-risk)

Security notes:
  - Login and forgot-password use generic error messages (no user enumeration).
  - IP address is captured from the request and stored with tokens for auditing.
  - Bearer token auth only Ã¢â‚¬â€ no cookie handling in this phase.
"""

import os
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services import auth_service
from app.services.auth_service import AccountStatusError
from app.services import audit_service
from app.core.security import get_password_hash
from app.services.email_service import dispatch_email

# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _rate_limit_key(request: Request) -> str:
    """
    Key function for SlowAPI.
    In TESTING mode (TESTING=true env var) each request gets a unique key,
    so rate limit counters never accumulate across tests.
    In production, use the real client IP.
    """
    if os.getenv("TESTING", "").lower() == "true":
        return str(uuid.uuid4())
    return get_remote_address(request)


# SlowAPI limiter Ã¢â‚¬â€ key function extracts client IP (or test UUID)
limiter = Limiter(key_func=_rate_limit_key)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(
    request: Request,
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Register a new user account in pending approval state.

    - Role is **always** set to ``employee`` regardless of any input.
    - Account approval_status is set to ``pending``.
    - Returns the created user profile with instructions (no tokens issued).
    """
    try:
        user = auth_service.register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # Log user registration event
    audit_service.record_audit_event(
        db=db,
        action="user_registration",
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
        new_values={
            "email": user.email,
            "role": user.role,
            "department": user.department,
            "approval_status": user.approval_status,
        },
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent"),
    )

    # Email: notify user that their registration is under review (fire-and-forget)
    background_tasks.add_task(
        dispatch_email,
        user.email,
        "account_registration",
        recipient_name=(f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]),
    )
    return user


# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email + password, receive access + refresh tokens.

    Returns a generic 401 on failure (no enumeration of valid emails).
    """
    ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent")

    try:
        user = auth_service.authenticate_user(db, payload.email, payload.password)
    except AccountStatusError as exc:
        audit_service.record_audit_event(
            db=db,
            action=exc.audit_action,
            actor_id=exc.user_id,
            entity_type="auth",
            entity_id=exc.user_id,
            new_values={"email": payload.email, "reason": str(exc)},
            ip_address=ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except ValueError as exc:
        # Record failed login attempt in audit logs
        audit_service.record_audit_event(
            db=db,
            action="login_failed",
            actor_id=None,
            entity_type="auth",
            new_values={"email": payload.email, "reason": str(exc)},
            ip_address=ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Record successful login event
    audit_service.record_audit_event(
        db=db,
        action="login_success",
        actor_id=user.id,
        entity_type="auth",
        entity_id=user.id,
        new_values={"email": user.email, "role": user.role},
        ip_address=ip,
        user_agent=user_agent,
    )

    return auth_service.create_token_pair(db, user, ip_address=ip, user_agent=user_agent)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh_token(
    request: Request,
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is rotated (single-use).
    """
    ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent")

    try:
        return auth_service.rotate_refresh_token(
            db, payload.refresh_token, ip_address=ip, user_agent=user_agent
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke the supplied refresh token (logout).
    Always returns 204 Ã¢â‚¬â€ idempotent and does not reveal token validity.
    """
    auth_service.revoke_refresh_token(db, payload.refresh_token)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/forgot-password
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Initiate a password reset.

    **Always** returns the same success response Ã¢â‚¬â€ the email address is never
    confirmed or denied (prevents user enumeration).

    In development (DEBUG=True) the raw reset token is returned in `reset_token`
    for testing convenience.  In production the token is dispatched via email only.
    """
    raw_token = auth_service.initiate_password_reset(db, payload.email)

    # Dispatch password-reset email (fire-and-forget Ã¢â‚¬â€ anti-enumeration safe)
    if raw_token:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        background_tasks.add_task(
            dispatch_email,
            payload.email,
            "password_reset",
            template_data={"reset_url": reset_url},
        )

    # Anti-enumeration: same body shape regardless of whether email exists
    response: dict = {
        "message": "If that email address is registered, a reset link has been sent."
    }
    _is_non_prod = (
        settings.DEBUG
        or os.getenv("TESTING", "").lower() == "true"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )
    if raw_token and _is_non_prod:
        # TESTING/DEV ONLY - omitted in production (DEBUG=False, TESTING unset)
        response["reset_token"] = raw_token
    return response


# ---------------------------------------------------------------------------
# POST /api/v1/auth/reset-password
# ---------------------------------------------------------------------------

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Complete a password reset using the token from forgot-password."""
    try:
        auth_service.complete_password_reset(db, payload.token, payload.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {"message": "Password has been reset successfully. Please log in."}


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile. Requires a valid JWT."""
    return current_user


# ---------------------------------------------------------------------------
# POST /api/v1/auth/change-password  (bonus Ã¢â‚¬â€ authenticated)
# ---------------------------------------------------------------------------

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    from app.core.security import verify_password

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}

