# SQLAlchemy 2.x Models & Alembic Migration Architecture - Phase 3

## 1. Overview
Phase 3 establishes the Object-Relational Mapping (ORM) and schema migration layer for the **Smart IT Helpdesk Management System** using **SQLAlchemy 2.x** and **Alembic**, backed by **PostgreSQL** via the modern `psycopg` (v3) driver.

---

## 2. Database Engine & Session Management

### 2.1 Engine Configuration (`app/db/session.py`)
- Created using `create_engine` with `postgresql+psycopg://` connection URL.
- **Connection Pooling**:
  - `pool_pre_ping=True`: Ensures stale or severed database connections are caught and recycled prior to execution.
  - `pool_size=10`: Maintains 10 steady-state pooled connections.
  - `max_overflow=20`: Allows up to 20 temporary burst connections during high load.
  - `pool_recycle=1800`: Automatically recycles connections every 30 minutes to prevent resource leakages on PostgreSQL.

### 2.2 Session Management (`SessionLocal` & `get_db`)
- `sessionmaker` configured with `autocommit=False`, `autoflush=False`, and `expire_on_commit=False`.
- `get_db()` is implemented as a Python generator yielding a request-scoped `Session` object:
  ```python
  def get_db() -> Generator[Session, None, None]:
      db = SessionLocal()
      try:
          yield db
      except Exception:
          db.rollback()
          raise
      finally:
          db.close()
  ```
  **Security Guarantees**:
  - Sessions are never exposed globally or shared across threads/requests.
  - Transactions roll back automatically on unhandled exceptions.
  - Connections are strictly closed and returned to the pool in the `finally` block.

---

## 3. SQLAlchemy 2.0 Declarative Models

All models reside under `backend/app/models/` and inherit from `Base` (`DeclarativeBase`) and `TimestampMixin` (`app/db/base.py`).

### 3.1 `User` (`app/models/user.py`)
- **Table**: `users`
- **Fields**: `id`, `email`, `password_hash`, `first_name`, `last_name`, `role`, `phone`, `department`, `is_active`, `created_at`, `updated_at`.
- **Relationships**:
  - `requested_tickets`: One-to-many relationship with `Ticket` (`foreign_keys="Ticket.requester_id"`).
  - `assigned_tickets`: One-to-many relationship with `Ticket` (`foreign_keys="Ticket.assigned_to"`).
  - `comments`: One-to-many with `Comment`.
  - `attachments`: One-to-many with `Attachment`.
  - `audit_logs`: One-to-many with `AuditLog`.
  - `refresh_tokens`: One-to-many with `RefreshToken` (`cascade="all, delete-orphan"`).
  - `password_reset_tokens`: One-to-many with `PasswordResetToken` (`cascade="all, delete-orphan"`).
- **Constraints**: `chk_users_role` (`role IN ('employee', 'technician', 'admin')`), unique `email`.

### 3.2 `Category` (`app/models/category.py`)
- **Table**: `categories`
- **Fields**: `id`, `name`, `description`, `is_active`, `created_at`, `updated_at`.
- **Relationships**: `tickets` (One-to-many with `Ticket`).

### 3.3 `Ticket` (`app/models/ticket.py`)
- **Table**: `tickets`
- **Fields**: `id`, `ticket_number`, `title`, `description`, `status`, `priority`, `category_id`, `requester_id`, `assigned_to`, `resolved_at`, `closed_at`, `created_at`, `updated_at`.
- **Foreign Keys**:
  - `category_id` -> `categories.id` (`ondelete="RESTRICT"`, `onupdate="CASCADE"`)
  - `requester_id` -> `users.id` (`ondelete="RESTRICT"`, `onupdate="CASCADE"`)
  - `assigned_to` -> `users.id` (`ondelete="SET NULL"`, `onupdate="CASCADE"`)
- **Relationships**:
  - `category`: Many-to-one with `Category`.
  - `requester`: Many-to-one with `User`.
  - `assignee`: Many-to-one with `User`.
  - `comments`: One-to-many with `Comment` (`cascade="all, delete-orphan"`).
  - `attachments`: One-to-many with `Attachment` (`cascade="all, delete-orphan"`).
  - `audit_logs`: One-to-many with `AuditLog` (`cascade="all, delete-orphan"`).
- **Constraints**: `chk_tickets_status`, `chk_tickets_priority`, resolution/closed timestamp order checks.

### 3.4 `Comment` (`app/models/comment.py`)
- **Table**: `comments`
- **Fields**: `id`, `ticket_id`, `user_id`, `comment_text`, `is_internal`, `created_at`, `updated_at`.
- **Foreign Keys**: `ticket_id` (`CASCADE`), `user_id` (`RESTRICT`).
- **Constraint**: `chk_comments_non_empty` (`LENGTH(TRIM(comment_text)) > 0`).

### 3.5 `Attachment` (`app/models/attachment.py`)
- **Table**: `attachments`
- **Fields**: `id`, `ticket_id`, `uploaded_by`, `file_name`, `file_path`, `file_size_bytes`, `mime_type`, `created_at`.
- **Constraint**: `chk_attachments_file_size` (1 byte to 50 MB).

### 3.6 `AuditLog` (`app/models/audit_log.py`)
- **Table**: `audit_logs`
- **Fields**: `id` (`BIGINT`), `ticket_id`, `actor_id`, `action`, `old_values` (`JSONB`), `new_values` (`JSONB`), `ip_address`, `user_agent`, `created_at`.

### 3.7 `RefreshToken` (`app/models/refresh_token.py`)
- **Table**: `refresh_tokens`
- **Fields**: `id`, `user_id`, `token_hash` (`UNIQUE`), `expires_at`, `is_revoked`, `created_at`, `revoked_at`, `ip_address`, `user_agent`.

### 3.8 `PasswordResetToken` (`app/models/password_reset_token.py`)
- **Table**: `password_reset_tokens`
- **Fields**: `id`, `user_id`, `token_hash` (`UNIQUE`), `expires_at`, `is_used`, `created_at`, `used_at`, `ip_address`.

---

## 4. Alembic Migrations

### 4.1 Configuration
- `backend/alembic.ini`: Root Alembic configuration.
- `backend/alembic/env.py`: Dynamically imports `settings.sync_database_url` and loads all models into `target_metadata = Base.metadata`.
- Initial revision script: `backend/alembic/versions/58ef887e8c67_initial_schema_all_models.py`.

### 4.2 Offline Migration Execution
The migration generates transactional DDL matching PostgreSQL 12+:
```powershell
alembic upgrade head --sql
```
And to apply online once PostgreSQL database credentials are authenticated:
```powershell
alembic upgrade head
```

---

## 5. FastAPI Database Dependency & Connectivity Verification

FastAPI routes can safely inject database sessions using `Depends(get_db)`:
```python
@router.get("/health/db", tags=["Health"])
def database_health_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {"status": "connected" if result == 1 else "unexpected_result", "database": "PostgreSQL"}
    except Exception as e:
        return {"status": "disconnected", "database": "PostgreSQL", "error": str(e)}
```
When database servers undergo maintenance or disconnect, exceptions are intercepted cleanly without crashing the API process or leaking stack traces.
