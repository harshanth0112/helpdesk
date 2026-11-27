"""
app/services/attachment_service.py - Secure File Upload & Download Service.

Security Rules:
- Enforce strict file extension allowlist: .png, .jpg, .jpeg, .pdf, .txt, .docx, .xlsx
- Enforce MIME type verification
- Enforce file size limit (max 10MB per file)
- Sanitize original filename (remove directory traversal characters like ../, ..\\)
- Generate cryptographically secure random UUID server-side storage filename
- Verify user has ticket access before downloading
- Prevent executable extensions (.exe, .sh, .bat, .js, .py, .php, etc.)
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import Tuple, List
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.user import User
from app.models.ticket import Ticket
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.core.permissions import check_ticket_access
from app.services.ticket_service import log_audit

UPLOAD_DIR = Path("uploads/tickets").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".txt", ".docx", ".xlsx"}

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def sanitize_filename(filename: str) -> str:
    """Strip path traversal components."""
    clean = os.path.basename(filename)
    clean = clean.replace("..", "").replace("/", "").replace("\\", "").strip()
    return clean or "unnamed_attachment"


async def save_attachment(
    db: Session,
    ticket_id: int,
    file: UploadFile,
    user: User,
) -> Attachment:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise ResourceNotFoundError("Ticket not found.")

    check_ticket_access(user, ticket)

    # 1. Filename & extension validation
    original_name = sanitize_filename(file.filename or "file")
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 2. Read contents & verify file size
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload an empty file.",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # 3. MIME type verification
    detected_mime, _ = mimetypes.guess_type(original_name)
    mime_type = file.content_type or detected_mime or "application/octet-stream"

    if mime_type not in ALLOWED_MIME_TYPES and ext not in {".txt", ".docx", ".xlsx"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{mime_type}' is not allowed.",
        )

    # 4. Generate random server-side filename to prevent file execution or overwrite
    random_filename = f"{uuid.uuid4().hex}{ext}"
    destination_path = UPLOAD_DIR / random_filename

    # Save to disk
    with open(destination_path, "wb") as f:
        f.write(content)

    # 5. Persist Attachment record in DB
    attachment = Attachment(
        ticket_id=ticket.id,
        uploaded_by=user.id,
        file_name=original_name,
        file_path=str(destination_path),
        file_size_bytes=file_size,
        mime_type=mime_type,
    )
    db.add(attachment)

    log_audit(
        db,
        ticket_id=ticket.id,
        actor_id=user.id,
        action="attachment_uploaded",
        new_values={"file_name": original_name, "file_size": file_size},
    )
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment_for_download(
    db: Session,
    attachment_id: int,
    user: User,
) -> Tuple[Attachment, Path]:
    attachment = db.get(Attachment, attachment_id)
    if not attachment or attachment.deleted_at is not None:
        raise ResourceNotFoundError("Attachment not found.")

    ticket = db.get(Ticket, attachment.ticket_id)
    if not ticket or ticket.deleted_at is not None:
        raise ResourceNotFoundError("Associated ticket not found.")

    check_ticket_access(user, ticket)

    file_path = Path(attachment.file_path).resolve()

    # Path traversal safety check: ensure path is strictly within UPLOAD_DIR
    if not str(file_path).startswith(str(UPLOAD_DIR)) or not file_path.exists():
        raise ResourceNotFoundError("File not found on server storage.")

    return attachment, file_path
