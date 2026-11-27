"""
app/core/dependencies.py — FastAPI dependency injectors for auth.

Provides:
  - ``get_current_user``: extracts + validates the Bearer JWT, loads the User
    row from the database, and verifies the account is active.
  - ``require_role(*roles)``: factory that returns a dependency which raises
    HTTP 403 when the authenticated user does not hold one of the allowed roles.

Security notes:
  - ``oauth2_scheme`` uses ``auto_error=False`` so we can return a custom 401
    body instead of FastAPI's default "Not authenticated" string.
  - If the JWT is missing, malformed, expired, or points to an unknown / inactive
    user, a generic 401 is raised — no information about *why* is leaked.
"""

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_jwt_token
from app.db.session import get_db
from app.models.user import User

# OAuth2 token extraction — reads the Authorization: Bearer <token> header.
# auto_error=False lets us craft our own 401 response.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that resolves the authenticated User from a valid JWT.

    Raises HTTP 401 for:
    - Missing token
    - Invalid / expired token
    - ``sub`` claim missing or not a valid integer
    - User not found in database
    - User account is inactive (``is_active = False``)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_jwt_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user: User | None = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise credentials_exception
    if user.approval_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting administrator approval.",
        )
    if user.approval_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration was not approved. Contact the administrator.",
        )
    if user.approval_status == "suspended" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact the administrator.",
        )
    return user


def require_role(*roles: str) -> Callable:
    """
    Dependency factory — returns a checker that raises HTTP 403 if the
    authenticated user's role is not in *roles*.

    Usage::

        @router.delete("/admin/users/{id}")
        def delete_user(current_user: User = Depends(require_role("admin"))):
            ...
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return checker
