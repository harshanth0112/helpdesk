# System Threat Model — Smart IT Helpdesk Management System

## 1. Overview & Architecture Scope

The Smart IT Helpdesk Management System is a multi-tier SaaS platform consisting of:
- **Client Tier**: React (Vite, Tailwind CSS, Axios) operating in browser runtime.
- **API Tier**: Python FastAPI application exposing `/api/v1` routes with SlowAPI rate limiting.
- **Data Tier**: PostgreSQL relational database with SQLAlchemy 2.0 ORM and Alembic migrations.
- **Storage Tier**: Local isolated filesystem (`uploads/tickets/`) for user-uploaded documents and screenshots.

---

## 2. Threat Modeling Methodology (STRIDE)

| STRIDE Category | Threat Description | Architectural Mitigation | Status |
|---|---|---|---|
| **Spoofing Identity** | Adversary assumes identity of another user or technician. | Argon2id password hashing, 15-minute JWT tokens with HMAC-SHA256 signature, 256-bit cryptographically secure refresh token rotation stored as SHA-256 digests. | **Mitigated** |
| **Tampering with Data** | Attendant modifies ticket priority, status, or assignee without authorization. | Backend allowlist schemas (`TicketPutUpdate`, `TicketStatusUpdate`, `TicketAssignUpdate`). Frontend role claims are ignored; backend verifies ownership for every object mutation. | **Mitigated** |
| **Repudiation** | User denies altering ticket state or assigning technicians. | Immutable `audit_logs` record `actor_id`, `action`, `old_values`, `new_values`, IP address, and server timestamps on all mutations. | **Mitigated** |
| **Information Disclosure** | IDOR: Attacker queries arbitrary ticket IDs or unassigned tickets; user enumeration on login/reset. | Uniform error messages on auth; queries return `404 Not Found` (rather than `403`) for unauthorized ticket access preventing IDOR enumeration. Internal notes stripped for employees. | **Mitigated** |
| **Denial of Service** | Volumetric brute-force login attempts or memory exhaustion through oversized pagination requests. | SlowAPI client-IP rate limiting (5 req/min on `/auth/login`, 10 req/min on `/auth/register`). Paging parameters bounded strictly to `max(1, min(page_size, 100))`. | **Mitigated** |
| **Elevation of Privilege** | Employee attempts role modification or assigns themselves as administrator. | Registration route strictly binds role to `employee`. Role adjustment is gated by `require_role("admin")`. | **Mitigated** |

---

## 3. Trust Boundaries & Data Flow

```
[ Unauthenticated Internet ]
           │
           ▼ (HTTPS / TLS)
[ Reverse Proxy / API Gateway ]
           │
┌──────────▼────────────────────────┐
│ FastAPI Application Boundary      │
│  - SlowAPI Rate Limiter           │
│  - CORS Middleware                │
│  - Security Response Headers      │
│  - JWT Bearer Authentication      │
│  - Role / Ownership Authorization │
└──────────┬───────────────────┬────┘
           │                   │
           ▼ (Parameterized)   ▼ (Sanitized UUID path)
    [ PostgreSQL DB ]    [ Isolated Storage ]
```

---

## 4. Attack Surface Analysis

| Surface | Potential Vulnerability | Implemented Security Control |
|---|---|---|
| `/api/v1/auth/login` | Brute-force credential guessing | 5 failed attempts locks account for 15 minutes (`locked_until`); IP rate limited to 5 req/min. |
| `/api/v1/tickets` | Query parameter SQL injection | Whitelisted sorting fields (`ALLOWED_SORT_FIELDS`); SQLAlchemy parameterized queries. |
| `/api/v1/tickets/{id}/attachments` | Arbitrary file upload / Remote Code Execution | Extension allowlist (`.png`, `.jpg`, `.pdf`, `.txt`, `.docx`), MIME validation, 10MB cap, stored with random UUID. |
| `/api/v1/tickets/attachments/{id}/download` | Path traversal (`../../etc/passwd`) | Filenames sanitized via `os.path.basename`; file paths validated against `UPLOAD_DIR.resolve()`. |
| `/api/v1/auth/forgot-password` | Account existence enumeration | Identical generic HTTP 200 response returned whether email is registered or unregistered. |
