# Deployment Guide — Smart IT Helpdesk Management System

> Phase 12 — Production deployment on **Render** (frontend + backend) with **Railway PostgreSQL**.

---

## Architecture

```
Browser
  │  HTTPS
  ▼
Render Static Site  (React + Vite)
  │  HTTPS  VITE_API_BASE_URL
  ▼
Render Web Service  (FastAPI + Uvicorn)
  │  postgresql+psycopg://  DATABASE_URL
  ▼
Railway PostgreSQL
```

---

## 1. Railway PostgreSQL

### 1.1 Create a project and provision the database

1. Log in to [railway.app](https://railway.app).
2. **New Project → Provision PostgreSQL**.
3. Click the **PostgreSQL** service → **Connect** tab.
4. Copy the **DATABASE_URL** (format: `postgresql://USER:PASS@HOST:PORT/DB`).

> [!IMPORTANT]
> Railway may emit a `postgres://` URL. The backend `config.py` automatically normalises both `postgres://` and `postgresql://` to the `postgresql+psycopg://` driver dialect required by psycopg v3.

### 1.2 Obtain credentials

Under **Connect → Public networking** you will find:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Full connection string — paste directly into Render |

### 1.3 Backup before schema changes

Railway's free tier does not include automated backups.  
Before running migrations, manually dump:

```bash
pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%Y%m%d).dump
```

---

## 2. Backend — Render Web Service

### 2.1 Create the service

1. **New → Web Service** → connect your GitHub repository.
2. Set **Root Directory** to `backend`.
3. **Runtime**: Python.

### 2.2 Build and start commands

| Setting | Value |
|---------|-------|
| Build command | `pip install -r requirements.txt` |
| Start command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Python version | Set env var `PYTHON_VERSION=3.11.0` |

> [!NOTE]
> `alembic upgrade head` runs before Uvicorn starts, so migrations are always applied before traffic arrives. If the migration fails, Render will not start the service.

### 2.3 Environment variables (set in Render dashboard)

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | Paste Railway URL |
| `JWT_SECRET_KEY` | ✅ | `python -c "import secrets; print(secrets.token_hex(64))"` |
| `JWT_ALGORITHM` | ✅ | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | ✅ | `7` |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | ✅ | `30` |
| `FRONTEND_URL` | ✅ | `https://YOUR-FRONTEND.onrender.com` |
| `ALLOWED_ORIGINS` | ✅ | `https://YOUR-FRONTEND.onrender.com` |
| `ENVIRONMENT` | ✅ | `production` |
| `DEBUG` | ✅ | `False` |
| `PYTHON_VERSION` | ✅ | `3.11.0` |
| `N8N_EMAIL_WEBHOOK_URL` | Optional | Production n8n webhook URL (`https://<instance>.app.n8n.cloud/webhook/helpdesk/send-email`) |
| `N8N_EMAIL_WEBHOOK_SECRET` | Optional | Shared secret matching `X-Helpdesk-Secret` in n8n Header Auth |
| `EMAIL_SENDER_NAME` | Optional | `Smart IT Helpdesk` |
| `EMAIL_TIMEOUT_SECONDS` | Optional | `10` |

> [!CAUTION]
> Never put `DATABASE_URL`, `JWT_SECRET_KEY`, or any credential in the frontend's environment variables or in source control.

### 2.4 Connection pooling

Production uses a conservative pool (`pool_size=2`, `max_overflow=3`) to stay within Railway's connection limits on the free tier. Upgrade the Railway plan and increase these values when scaling.

---

## 3. Frontend — Render Static Site

### 3.1 Create the service

1. **New → Static Site** → connect your GitHub repository.
2. **Root Directory**: `frontend`.

### 3.2 Build settings

| Setting | Value |
|---------|-------|
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

### 3.3 Environment variable

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://YOUR-BACKEND.onrender.com` |

> [!WARNING]
> Vite bakes environment variables into the JavaScript bundle at build time. They are **public**. Never put secrets, database credentials, or JWT keys here.

### 3.4 SPA routing rewrite

`frontend/public/_redirects` contains:

```
/*    /index.html   200
```

This instructs Render's CDN to serve `index.html` for all paths, allowing React Router to handle navigation on the client. Without this, direct URL access (e.g. `/dashboard/tickets/5`) would return a 404.

---

## 4. Alembic Migrations

Migrations run automatically via the start command (`alembic upgrade head`).

### Manual run against Railway (local)

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://USER:PASS@HOST:PORT/DB"
alembic upgrade head
alembic current   # confirm revision
alembic history   # see full history
```

### Current migrations

| Revision | Description |
|----------|-------------|
| `58ef887e8c67` | Initial schema — all models |
| `a1b2c3d4e5f6` | Add login tracking to users |

---

## 5. Health Checks

| Endpoint | Description |
|----------|-------------|
| `GET /health` | App liveness — returns `{"status":"healthy"}` |
| `GET /health/db` | DB connectivity — executes `SELECT 1` |

Render uses `/health` as the default health-check path (configured in `render.yaml`).

---

## 6. Smoke Tests

After deployment, verify the following:

```bash
BASE=https://YOUR-BACKEND.onrender.com

# Liveness
curl $BASE/health

# DB connectivity
curl $BASE/health/db

# Auth
curl -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'
```

---

## 7. Known Limitations

- **File uploads** are served from the local filesystem. In production on Render's ephemeral filesystem, uploaded files will be lost on redeploy. Migrate uploads to a cloud storage service (e.g., Google Cloud Storage, AWS S3, or Cloudflare R2) before accepting production upload traffic.
- **Email delivery** is handled asynchronously via n8n Cloud + Gmail OAuth2 (`N8N_EMAIL_WEBHOOK_URL` and `N8N_EMAIL_WEBHOOK_SECRET`). If these variables are unset, email dispatch is skipped cleanly without blocking core helpdesk operations. See [`docs/n8n-integration-guide.md`](n8n-integration-guide.md).
- **Free-tier sleep**: Render free web services sleep after 15 minutes of inactivity. The first request after sleep may be slow. Upgrade to a paid plan or use an external uptime monitor.
- **Railway free-tier connections**: Capped at a small pool. Scale up the Railway plan if connection exhaustion errors appear.
