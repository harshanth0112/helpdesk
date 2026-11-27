"""
app/schemas/ticket.py - Comprehensive schemas for Ticket CRUD, pagination, filtering, and history.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Comment Schemas
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1)
    is_internal: bool = False


class CommentResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    comment_text: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Ticket Request Schemas
# ---------------------------------------------------------------------------

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category_id: int
    priority: str = Field(default="medium")
    tagged_user_ids: Optional[List[int]] = Field(default=None)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v.lower()


class TicketPutUpdate(BaseModel):
    """Full ticket update schema for PUT /api/v1/tickets/{id}"""
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category_id: Optional[int] = None


class TicketStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"open", "assigned", "in_progress", "pending", "resolved", "closed"}
        if v.lower() not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v.lower()


class TicketPriorityUpdate(BaseModel):
    priority: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v.lower()


class TicketAssignUpdate(BaseModel):
    assigned_to: Optional[int] = None  # None means unassign


# ---------------------------------------------------------------------------
# Ticket Response Schemas & Pagination
# ---------------------------------------------------------------------------

class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str
    category_id: int
    requester_id: int
    assigned_to: Optional[int] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: int
    actor_id: Optional[int]
    action: str
    old_values: Optional[Any] = None
    new_values: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTicketResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# User Administration Schemas
# ---------------------------------------------------------------------------

class UserRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"employee", "technician", "admin"}
        if v.lower() not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v.lower()


class UserApproveRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_approval_role(cls, v: str) -> str:
        allowed = {"employee", "technician", "admin"}
        if v.lower() not in allowed:
            raise ValueError("Allowed roles during approval are: employee, technician, admin.")
        return v.lower()


class UserRejectRequest(BaseModel):
    rejection_reason: Optional[str] = Field(None, max_length=500)


class UserStatusUpdate(BaseModel):
    action: str

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"suspend", "reactivate"}
        if v.lower() not in allowed:
            raise ValueError("Action must be either 'suspend' or 'reactivate'.")
        return v.lower()


# ---------------------------------------------------------------------------
# Category Schemas
# ---------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Soft Delete & Recycle Bin Schemas (Phase 15)
# ---------------------------------------------------------------------------

class SoftDeleteRequest(BaseModel):
    deletion_reason: Optional[str] = Field(None, max_length=500)


class AttachmentResponse(BaseModel):
    id: int
    ticket_id: int
    uploaded_by: int
    file_name: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RecycleBinItemResponse(BaseModel):
    id: int
    entity: str
    identifier: str
    title: str
    subtitle: str
    status: str
    deletion_status: str
    deleted_at: datetime
    deleted_by: Optional[int] = None
    deleted_by_name: Optional[str] = None
    deleted_by_email: Optional[str] = None
    deletion_reason: Optional[str] = None


class PaginatedRecycleBinResponse(BaseModel):
    entity: str
    items: List[RecycleBinItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RestoreResponse(BaseModel):
    status: str
    entity: str
    id: int
    restored_by: int
