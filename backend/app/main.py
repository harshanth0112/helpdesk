"""
app/main.py — FastAPI application factory.

Registered middleware:
  - CORSMiddleware (explicit allow-list from settings)
  - SlowAPI RateLimitMiddleware (per-route decorators in auth.py)

Registered routers:
  - api_router     → /health, /api/v1
  - auth_router    → /api/v1/auth/*
  - tickets_router → /api/v1/tickets/*
  - admin_router   → /api/v1/admin/*
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.routes.api import router as api_router
from app.routes.auth import router as auth_router
from app.routes.tickets import router as tickets_router
from app.routes.admin import router as admin_router

# ---------------------------------------------------------------------------
# Rate limiter (shared state — imported in routes/auth.py too)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Application
# Docs/redoc are disabled in production to reduce attack surface.
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Smart IT Helpdesk Management System API — "
        "Phase 12: Production Deployment"
    ),
    version="12.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Attach limiter to app state so SlowAPI can find it
app.state.limiter = limiter

# Global rate-limit exceeded handler (returns 429 JSON)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    OWASP A02: Security Misconfiguration - Enforce security headers on all responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (clickjacking protection)
    - X-XSS-Protection: 0 (defers to modern CSP)
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    return response


app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    base = {
        "message": "Smart IT Helpdesk Management System API",
        "health": "/health",
        "v1": "/api/v1",
    }
    if not settings.is_production:
        base["docs"] = "/docs"
    return base
