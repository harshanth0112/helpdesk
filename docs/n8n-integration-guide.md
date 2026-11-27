# n8n Cloud Gmail Integration Guide

> **Phase 14.2** — Asynchronous email automation for the Smart IT Helpdesk Management System using **FastAPI**, **n8n Cloud**, and **Gmail OAuth2**.

---

## 1. Architecture Overview

```
React Frontend (Render Static Site)
       │
       │ HTTPS REST API
       ▼
FastAPI Backend (Render Web Service)
       │
       │ BackgroundTasks -> dispatch_email()
       │ Authenticated HTTPS POST (X-Helpdesk-Secret)
       ▼
n8n Cloud Webhook (/webhook/helpdesk/send-email)
       │
       ├─► Validate Email Payload (Code Node)
       │     ├─ Invalid / disallowed fields ──► 400 Bad Request
       │     └─ Valid ──► Render HTML/Text Template
       │
       └─► Gmail - Send Message (Gmail OAuth2)
             ├─ Success ──► 200 OK
             └─ Error   ──► 502 Bad Gateway
```

### Responsibilities
- **FastAPI Backend**: Owns all business logic, authentication, RBAC, password-reset token generation, and PostgreSQL persistence. Dispatches email requests asynchronously via `BackgroundTasks` so HTTP responses are never blocked and business transactions are never rolled back on email delivery failure.
- **n8n Cloud**: Authenticates incoming webhook requests via `X-Helpdesk-Secret`, validates the JSON schema, renders the branded HTML/text email template, and sends the message through the connected Gmail OAuth2 account.

---

## 2. Backend Configuration

### Environment Variables (`backend/.env` / Render Dashboard)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `N8N_EMAIL_WEBHOOK_URL` | Yes (to send) | `""` | Production n8n webhook URL (`https://<instance>.app.n8n.cloud/webhook/helpdesk/send-email`) |
| `N8N_EMAIL_WEBHOOK_SECRET` | Yes (to send) | `""` | Shared secret matching the `X-Helpdesk-Secret` Header Auth credential in n8n |
| `EMAIL_SENDER_NAME` | No | `Smart IT Helpdesk` | Display name included in the payload |
| `EMAIL_TIMEOUT_SECONDS` | No | `10` | HTTP request timeout in seconds for `httpx.AsyncClient` |
| `FRONTEND_URL` | Yes | `http://localhost:5173` | Base URL used to construct password-reset links |

> [!NOTE]
> If `N8N_EMAIL_WEBHOOK_URL` or `N8N_EMAIL_WEBHOOK_SECRET` is blank, `dispatch_email()` logs a warning and skips sending without raising an exception. All core helpdesk features continue to work normally.

---

## 3. Integrated Email Events (6 Triggers)

| # | Event | Trigger Location | Template | Recipient |
|---|-------|-----------------|----------|-----------|
| 1 | Account Registration | `POST /api/v1/auth/register` (`auth.py`) | `account_registration` | Newly registered user |
| 2 | Account Approval | `PATCH /api/v1/admin/users/{id}/approve` (`admin.py`) | `account_approval` | Approved user |
| 3 | Account Rejection | `PATCH /api/v1/admin/users/{id}/reject` (`admin.py`) | `account_rejection` | Rejected user |
| 4 | Ticket Assignment | `PATCH /api/v1/tickets/{id}/assign` (`tickets.py`) | `ticket_assignment` | Assigned technician |
| 5 | Ticket Status Update | `PATCH /api/v1/tickets/{id}/status` (`tickets.py`) | `ticket_status_update` | Ticket requester |
| 6 | Password Reset | `POST /api/v1/auth/forgot-password` (`auth.py`) | `password_reset` | Requesting user |

---

## 4. Webhook Payload Contract

The backend sends JSON matching the verified n8n schema (`docs/n8n-workflow-smart-helpdesk-gmail.json`):

```json
{
  "to": "recipient@example.com",
  "template": "ticket_assignment",
  "email_type": "html",
  "sender_name": "Smart IT Helpdesk",
  "recipient_name": "Jane Doe",
  "template_data": {
    "ticket_id": "TKT-0042",
    "ticket_title": "VPN connection drops",
    "ticket_priority": "high"
  }
}
```

> [!IMPORTANT]
> Custom `subject` and `message` fields are also preserved by the n8n Code node for direct Postman/API testing compatibility.

---

## 5. Security Controls

1. **Header Authentication**: Every webhook call includes `X-Helpdesk-Secret` validated by n8n Header Auth.
2. **No Secrets in Source Control**: `N8N_EMAIL_WEBHOOK_SECRET` is only read from environment variables and never logged (`email_service.py` logs only template name, HTTP status code, or exception class name).
3. **Production Password Reset Protection**: `POST /api/v1/auth/forgot-password` omits `reset_token` from the HTTP response body when `DEBUG=False` and `TESTING` is unset, and raw reset tokens are never logged.
4. **HTML Escaping & Schema Allowlist**: The n8n Code node rejects unexpected payload attributes, validates email formats, enforces `https://` or `http://localhost` on `reset_url`, and HTML-escapes all dynamic values.
5. **Execution Data Retention**: The workflow JSON configures `saveDataErrorExecution: "none"`, `saveDataSuccessExecution: "none"`, and `saveManualExecutions: false` so sensitive payloads (such as password-reset links) are not retained in n8n execution logs.
