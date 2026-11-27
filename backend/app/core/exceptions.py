"""
app/core/exceptions.py - Centralized Authorization and Access Control Exceptions.
"""

from fastapi import HTTPException, status


class PermissionDeniedError(HTTPException):
    def __init__(self, detail: str = "You do not have permission to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ResourceNotFoundError(HTTPException):
    """
    Used when a resource does not exist or user should not know it exists (IDOR prevention).
    """
    def __init__(self, detail: str = "Resource not found."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class PrivilegeEscalationError(HTTPException):
    def __init__(self, detail: str = "Privilege escalation detected: unauthorized role assignment."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource conflict."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
