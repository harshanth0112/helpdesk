# OWASP Security Checklist & Verification

## 1. OWASP Top 10: 2025 Review

| Category | Requirement | Implementation Status | Evidence / Verification |
|---|---|:---:|---|
| **A01: Broken Access Control** | Deny-by-default, object-level ownership checks, no client-trusted roles, anti-IDOR. | ✅ Pass | `app/core/permissions.py`: `check_ticket_access` enforces ownership or raises `404`. Gated with `require_role`. |
| **A02: Security Misconfiguration** | CORS restricted to development origin, secure response headers, disable unnecessary features. | ✅ Pass | Explicit CORS allowlist (`http://localhost:5173`); `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS`. |
| **A03: Software Supply Chain** | Scan package dependencies for vulnerabilities; keep pinned versions. | ✅ Pass | `npm audit` returned 0 vulnerabilities; `bandit` scan reported 0 high/medium issues. |
| **A04: Cryptographic Failures** | Strong password hashing, secure token generation, no sensitive storage in plaintext. | ✅ Pass | Argon2id password hashing; `secrets.token_urlsafe(32)` tokens stored strictly as SHA-256 hashes. |
| **A05: Injection** | SQL injection protection, ORM parameterization, stored XSS prevention. | ✅ Pass | SQLAlchemy 2.0 ORM parameterization; allowlisted sort fields; React default HTML escaping. |
| **A06: Insecure Design** | Threat modeling, secure state transitions, brute-force mitigation. | ✅ Pass | State machine in `app/core/ticket_state.py`; SlowAPI rate limiting; 5-attempt brute-force lockout. |
| **A07: Identification & Auth Failures** | Short-lived tokens, rotation with reuse detection, anti-enumeration. | ✅ Pass | 15-min JWT; refresh rotation invalidates token family on replay; generic login/password reset messages. |
| **A08: Software & Data Integrity** | Secure upload validation, verify file extensions and MIME types, random server-side names. | ✅ Pass | `attachment_service.py` enforces allowlist (`.png`, `.jpg`, `.pdf`), checks size $\le 10\text{MB}$, saves as UUIDs. |
| **A09: Security Logging & Monitoring** | Audit trail of administrative actions, status mutations, role modifications. | ✅ Pass | `audit_logs` records actor ID, action, old/new states, timestamps, and IP addresses. |
| **A10: Mishandling of Exceptions** | Fail-secure defaults, no internal stack trace exposure to API consumers. | ✅ Pass | Centralized `HTTPException` handlers with generic error messages and safe HTTP error status codes. |

---

## 2. OWASP API Security Top 10: 2023 Review

| API Category | Description | Protection Mechanism |
|---|---|---|
| **API1: BOLA (Broken Object Level Authorization)** | Accessing unauthorized tickets/comments via ID parameter. | Ownership verified before data access; unauthorized attempts yield `404 Not Found` (anti-IDOR). |
| **API2: Broken Authentication** | Compromised credentials or token forgery. | Argon2id, signed JWTs with expiration verification, refresh token reuse detection. |
| **API3: BOPLA (Broken Object Property Level Auth)** | Mass assignment of unauthorized fields (`role`, `assigned_to`). | Disallowed fields stripped by Pydantic schemas (`TicketPutUpdate`, `RegisterRequest`). |
| **API4: Unrestricted Resource Consumption** | Large payload attacks, unbounded pagination, DoS requests. | 10MB upload ceiling; page size bounded to 100 max; SlowAPI IP rate limiting. |
| **API5: BFLA (Broken Function Level Authorization)** | Accessing administrative endpoints (`/admin/*`). | Protected by `Depends(require_role("admin"))` which checks verified JWT token role claims. |
| **API6: Unrestricted Access to Sensitive Business Flows** | Automated brute-force ticket spam or credential stuffing. | Strict per-route rate limits (5/min login, 10/min register); account lockout after 5 failures. |
| **API7: Server Side Request Forgery (SSRF)** | Arbitrary URL requests from backend. | System does not make external web requests from user-supplied URLs. |
| **API8: Security Misconfiguration** | Verbose error leaks or open CORS. | Development origins whitelisted; debug errors sanitized; security headers enforced. |
| **API9: Improper Inventory Management** | Undocumented endpoints or deprecated versions. | Centralized API router versioned at `/api/v1` with automated OpenAPI `/docs`. |
| **API10: Unsafe Consumption of APIs** | Third-party service compromise. | No unauthenticated third-party dependencies consumed in the core critical path. |
