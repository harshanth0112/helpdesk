# Architecture Specification - Phase 1 Foundation

## 1. Overview
The **Smart IT Helpdesk Management System** is structured as a decoupled web application comprising a modern **React (Vite)** single-page application frontend and a high-performance **FastAPI (Python 3.10+)** REST backend.

Phase 1 establishes the foundational infrastructure, environment conventions, cross-origin communication policies, reusable UI component patterns, and operational verification endpoints.

---

## 2. System Architecture Diagram

```
+-----------------------------------------------------------+
|                 Client Browser (Vite SPA)                 |
|                   http://127.0.0.1:5173                   |
|                                                           |
|  +--------------------+        +-----------------------+  |
|  |     MainLayout     |        |       HomePage        |  |
|  |  (Navbar / Footer) |        | (Health Status Cards) |  |
|  +--------------------+        +-----------------------+  |
|                         |                                 |
|                         v                                 |
|              services/api.js (Axios)                      |
+---------------------------+-------------------------------+
                            |
                     HTTP / JSON
           (CORS restricted to 5173 origins)
                            |
                            v
+-----------------------------------------------------------+
|                   FastAPI Backend Server                  |
|                   http://127.0.0.1:8000                   |
|                                                           |
|  +-----------------------------------------------------+  |
|  |                  CORSMiddleware                     |  |
|  |     Origins: http://localhost:5173, 127.0.0.1:5173  |  |
|  +-----------------------------------------------------+  |
|                         |                                 |
|  +----------------------+------------------------------+  |
|  | Root & Router Endpoints                             |  |
|  |   - GET /health   -> Health check status payload    |  |
|  |   - GET /api/v1   -> Versioned entry point          |  |
|  |   - GET /docs     -> OpenAPI / Swagger UI           |  |
|  +-----------------------------------------------------+  |
+-----------------------------------------------------------+
```

---

## 3. Directory Layout and Separation of Concerns

```
smart-helpdesk/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Package initialization
│   │   ├── main.py              # FastAPI application instance, CORS, middleware & root endpoints
│   │   ├── config.py            # Pydantic BaseSettings, env parsing & CORS origins validation
│   │   └── routes/
│   │       ├── __init__.py      # Routes package definition
│   │       └── api.py           # API endpoints (GET /health, GET /api/v1)
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py          # Pytest integration tests for endpoints
│   ├── requirements.txt         # Pinned python dependencies
│   ├── .env.example             # Template for backend environment variables
│   └── .env                     # Local configuration (not committed to public VCS)
├── frontend/
│   ├── src/
│   │   ├── components/          # Atomic reusable UI components (Navbar, Footer, Card)
│   │   ├── layouts/             # Page structural templates (MainLayout with Outlet)
│   │   ├── pages/               # Route views (HomePage with health check query)
│   │   ├── services/            # Axios API clients and HTTP abstractions (api.js)
│   │   ├── hooks/               # Custom React hooks (reserved for Phase 2+)
│   │   ├── context/             # Application state contexts (reserved for Phase 2+)
│   │   ├── App.jsx              # React Router configuration
│   │   ├── main.jsx             # React DOM entry point
│   │   └── index.css            # Tailwind CSS root stylesheet
│   ├── index.html               # Vite HTML template
│   ├── vite.config.js           # Vite server, React, and Tailwind CSS plugin configuration
│   ├── package.json             # NPM dependencies and scripts
│   ├── .env.example             # Template for frontend environment variables
│   └── .env                     # Local environment variables (VITE_API_BASE_URL)
├── docs/
│   └── architecture.md          # System architecture and technical decisions
└── README.md                    # Project setup, execution instructions, and Phase 1 documentation
```

---

## 4. Frontend Component & Service Structure

1. **`services/api.js`**:
   - Encapsulates Axios client with `import.meta.env.VITE_API_BASE_URL` defaulting to `http://127.0.0.1:8000`.
   - Exports typed asynchronous helper methods (`checkHealth`, `getApiV1Info`).
2. **`components/`**:
   - `Navbar`: Global branding header with phase status indicators.
   - `Footer`: Global footer metadata.
   - `Card`: Reusable dashboard container supporting icons, badges, and customizable children.
3. **`layouts/MainLayout.jsx`**:
   - Houses the shared application layout, injecting page contents via React Router DOM's `<Outlet />`.
4. **`pages/HomePage.jsx`**:
   - Executes non-blocking API health queries on mount.
   - Handles loading states, failure fallbacks, and formatted JSON rendering.

---

## 5. Backend Configuration & CORS Policy

- **Pydantic Settings (`app/config.py`)**:
  - Dynamically reads configuration from `.env`.
  - Parses comma-separated origin strings into a clean list of allowed CORS origins.
- **Explicit Development CORS (`app/main.py`)**:
  - Only allowed frontend origins (`http://localhost:5173` and `http://127.0.0.1:5173`) are whitelisted.
  - Wildcards (`*`) are disallowed for credentials mode to ensure strict security compliance.

---

## 6. Phase 1 Non-Functional & Boundary Invariants

- **No Database Persistence**: No SQLAlchemy, Alembic migrations, or database tables created in Phase 1.
- **No Mock Business Entities**: No dummy tickets, users, or queues implemented.
- **No Authentication Logic**: OAuth, JWT tokens, and user credentials will be introduced in subsequent phases.

---

## Phase 12 — Production Architecture (Render + Railway)

### Production System Diagram

```
╔══════════════════════════════════════════════════════════════╗
║               End User Browser (Any Device)                  ║
╚══════════════════════════════╤═══════════════════════════════╝
                               │ HTTPS (TLS 1.2+)
                               ▼
╔══════════════════════════════════════════════════════════════╗
║          Render Static Site — React + Vite (CDN)             ║
║  URL: https://YOUR-FRONTEND.onrender.com                     ║
║                                                              ║
║  Build:   npm install && npm run build                       ║
║  Publish: dist/                                              ║
║  Routing: _redirects → /* /index.html 200 (SPA fallback)     ║
║                                                              ║
║  Env vars (public, baked at build time):                     ║
║    VITE_API_BASE_URL = https://YOUR-BACKEND.onrender.com     ║
╚══════════════════════════════╤═══════════════════════════════╝
                               │ HTTPS  /api/v1/*
                               ▼
╔══════════════════════════════════════════════════════════════╗
║          Render Web Service — FastAPI + Uvicorn              ║
║  URL: https://YOUR-BACKEND.onrender.com                      ║
║                                                              ║
║  Build:  pip install -r requirements.txt                     ║
║  Start:  alembic upgrade head &&                             ║
║          uvicorn app.main:app --host 0.0.0.0 --port $PORT    ║
║                                                              ║
║  Middleware:                                                  ║
║    CORSMiddleware (exact origin allow-list)                   ║
║    SlowAPIMiddleware (rate limiting)                          ║
║    Security headers (HSTS, X-Frame-Options, nosniff …)       ║
║                                                              ║
║  Env vars (private, Render dashboard):                        ║
║    DATABASE_URL, JWT_SECRET_KEY, FRONTEND_URL,               ║
║    ALLOWED_ORIGINS, ENVIRONMENT=production, DEBUG=False       ║
╚══════════════════════════════╤═══════════════════════════════╝
                               │ postgresql+psycopg://
                               │ DATABASE_URL (Railway public)
                               ▼
╔══════════════════════════════════════════════════════════════╗
║          Railway PostgreSQL                                  ║
║                                                              ║
║  Driver:   psycopg v3 (psycopg[binary])                      ║
║  ORM:      SQLAlchemy 2.x                                    ║
║  Pooling:  pool_size=2, max_overflow=3 (free tier)           ║
║  Recycle:  1800 s                                            ║
║  Schemas:  applied by Alembic (2 migrations)                 ║
╚══════════════════════════════════════════════════════════════╝
```

### Environment Variables

| Variable | Service | Sensitive |
|----------|---------|-----------|
| `VITE_API_BASE_URL` | Frontend (Render) | No — public build |
| `DATABASE_URL` | Backend (Render) | **Yes** |
| `JWT_SECRET_KEY` | Backend (Render) | **Yes** |
| `JWT_ALGORITHM` | Backend (Render) | No |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | No |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Backend | No |
| `FRONTEND_URL` | Backend | No |
| `ALLOWED_ORIGINS` | Backend | No |
| `ENVIRONMENT` | Backend | No |
| `DEBUG` | Backend | No |

### Database URL Normalisation

The `config.py` `sync_database_url` property handles all Railway URL variants:

| Input | Normalised to |
|-------|--------------|
| `postgres://…` | `postgresql+psycopg://…` |
| `postgresql://…` | `postgresql+psycopg://…` |
| `postgresql+psycopg://…` | unchanged |

### Connection Pooling Strategy

| Environment | pool_size | max_overflow | Rationale |
|-------------|-----------|--------------|-----------|
| Production | 2 | 3 | Stay within Railway free-tier connection limit |
| Development | 10 | 20 | Support concurrent test runners |

---

## Phase 14.2 — Asynchronous Email Automation (n8n Cloud + Gmail OAuth2)

Transactional email delivery is decoupled from FastAPI request latency using `BackgroundTasks` and `backend/app/services/email_service.py`:

```
FastAPI Route (sync)
  └─► BackgroundTasks.add_task(dispatch_email, ...)
        └─► httpx.AsyncClient POST (X-Helpdesk-Secret, timeout=10s)
              └─► n8n Cloud Webhook (/webhook/helpdesk/send-email)
                    ├─► Validate Email Payload & Render HTML Template
                    └─► Gmail OAuth2 -> Recipient Inbox
```

- Email failures are logged (without secrets or raw tokens) and never roll back database transactions.
- See [`docs/n8n-integration-guide.md`](n8n-integration-guide.md) and [`docs/email-template-catalog.md`](email-template-catalog.md).
