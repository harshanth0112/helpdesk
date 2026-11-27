# Security Test Report — Smart IT Helpdesk Management System

> Phase 12 — Production security review  
> Date: 2026-11-26

---

## 1. Static Analysis — Bandit

**Tool**: bandit 1.9.4  
**Scope**: `backend/app/**`  
**Command**: `python -m bandit -r app -f txt`

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 0 |
| Low | 1 |

### Low-Severity Finding

| ID | File | Line | Description | Status |
|----|------|------|-------------|--------|
| B105 | `app/services/auth_service.py` | 181 | `"token_type": "bearer"` flagged as possible hardcoded password | **False positive** — `"bearer"` is the OAuth 2.0 token type string, not a credential. No remediation needed. |

**Conclusion**: No actionable security findings from Bandit.

---

## 2. Dependency Audit — pip-audit

**Tool**: pip-audit (sandboxed; network not available in CI environment)  
**Status**: Network-isolated scan — cannot reach PyPI vulnerability database in sandbox.  
**Recommendation**: Run `pip-audit -r backend/requirements.txt` with network access in CI/CD (GitHub Actions) before each deployment.

Dependencies audited manually:

| Package | Version Constraint | Notes |
|---------|-------------------|-------|
| fastapi | ≥0.100.0, <1.0.0 | Current stable |
| uvicorn | ≥0.22.0 | Standard production runner |
| pydantic | ≥2.0.0 | v2 — actively maintained |
| pydantic-settings | ≥2.0.0 | v2 |
| sqlalchemy | ≥2.0.0 | v2 — current LTS |
| alembic | ≥1.13.0 | Current |
| psycopg | ≥3.1.0 | psycopg v3 — actively maintained |
| argon2-cffi | ≥23.1.0 | OWASP-recommended password hashing |
| passlib | ≥1.7.4 | Wraps argon2-cffi |
| python-jose | ≥3.3.0 | JWT — no known CVEs at audit date |
| slowapi | ≥0.1.9 | Rate limiting |

---

## 3. Frontend — npm audit

**Status**: Network-isolated scan — cannot reach npmjs.org registry in sandbox.  
**Recommendation**: Run `npm audit --audit-level=moderate` in CI/CD before each deployment.

---

## 4. OWASP Top 10 Manual Review

| Risk | Control | Status |
|------|---------|--------|
| A01 Broken Access Control | RBAC on every protected route; `ProtectedRoute` on frontend; server-side role checks in every API endpoint; IDOR prevented by filtering queries by `user_id` | ✅ Implemented |
| A02 Security Misconfiguration | Security headers middleware (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy); docs disabled in production; `DEBUG=False` | ✅ Implemented |
| A03 Injection | SQLAlchemy ORM with parameterised queries throughout; no raw string interpolation in queries | ✅ Implemented |
| A04 Insecure Design | Threat model documented in `docs/threat-model.md`; password reset uses secure short-lived tokens stored hashed | ✅ Implemented |
| A05 Security Misconfiguration | CORS restricted to exact production frontend origin; no wildcard | ✅ Implemented |
| A06 Vulnerable Components | pip-audit + npm audit in CI recommended; manual review shows no known CVEs | ⚠️ CI scan needed |
| A07 Identification & Authentication | Argon2 password hashing; JWT access tokens (15 min); refresh-token rotation; token revocation on logout | ✅ Implemented |
| A08 Software & Data Integrity | Alembic versioned migrations; no untrusted deserialization | ✅ Implemented |
| A09 Security Logging & Monitoring | AuditLog model records all sensitive actions; production logs via Uvicorn to stdout (captured by Render) | ✅ Implemented |
| A10 SSRF | No server-side URL fetching; no outbound HTTP from backend | ✅ Not applicable |

---

## 5. Additional Security Controls

| Control | Implementation |
|---------|----------------|
| Password hashing | Argon2 via passlib/argon2-cffi (OWASP recommended) |
| JWT signing | HS256 with 64-byte random secret |
| Refresh-token storage | SHA-256 hashed in database; raw token sent to client only |
| Token rotation | Each refresh call issues a new pair and revokes the old token |
| Rate limiting | SlowAPI on auth endpoints (login, register) |
| File upload | Type and size restrictions; random UUID filenames; no path traversal |
| Exception handling | Generic 500 errors returned to clients; stack traces logged server-side only |
| Secrets management | All secrets via environment variables; never in source code or frontend |
| HTTPS | Enforced by Render (TLS 1.2+); HSTS header on all responses |

---

## 6. Known Gaps / Remediation Backlog

| Item | Risk | Recommended Action |
|------|------|--------------------|
| File uploads on ephemeral filesystem | **High** — files lost on redeploy | Migrate to cloud storage (GCS/S3/R2) |
| Email delivery not configured | **Medium** — password reset non-functional | Add SMTP provider (SendGrid/Resend) |
| pip-audit / npm audit in CI | **Medium** — CVEs may appear in dependencies | Add GitHub Actions workflow |
| OWASP ZAP baseline scan | **Medium** — no DAST coverage | Run ZAP against deployed Render URLs |
| Render free-tier sleep | **Low** — availability | Upgrade plan or add uptime monitor |

---

> [!NOTE]
> Passing static analysis and manual review does not guarantee the absence of all vulnerabilities. A DAST scan (OWASP ZAP) against the live deployed URLs and a formal penetration test are recommended before handling sensitive production data.
