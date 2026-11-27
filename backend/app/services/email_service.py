"""
email_service.py — Reusable async email dispatch via n8n Cloud Gmail automation.

Design decisions:
- Uses httpx.AsyncClient for async calls that play well with FastAPI BackgroundTasks.
- Never logs secrets, raw tokens or full payloads.
- Never raises exceptions to caller — returns a result dict so business logic
  is never rolled back due to email failure (fire-and-forget pattern).
- All configuration comes from environment variables via settings.
- Recipient email is validated locally before the HTTP call.
- Supports all 6 email templates defined in the n8n workflow.

Usage (inside a sync FastAPI route via BackgroundTasks):

    from fastapi import BackgroundTasks
    from app.services.email_service import dispatch_email

    def my_route(background_tasks: BackgroundTasks, ...):
        background_tasks.add_task(
            dispatch_email,
            to="user@example.com",
            template="account_approval",
            recipient_name="Alice",
        )
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

SUPPORTED_TEMPLATES = {
    "account_registration",
    "account_approval",
    "account_rejection",
    "ticket_assignment",
    "ticket_status_update",
    "password_reset",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def dispatch_email(
    to: str,
    template: str,
    *,
    recipient_name: str | None = None,
    sender_name: str | None = None,
    reply_to: str | None = None,
    template_data: dict[str, Any] | None = None,
    email_type: str = "html",
) -> dict[str, Any]:
    """
    Dispatch an email through the n8n Cloud Gmail automation webhook.

    Parameters
    ----------
    to : str
        Recipient email address.  Validated locally before dispatch.
    template : str
        One of SUPPORTED_TEMPLATES.
    recipient_name : str, optional
        Display name used in the email greeting.
    sender_name : str, optional
        Sender display name (defaults to settings.EMAIL_SENDER_NAME).
    reply_to : str, optional
        Reply-to address for the email.
    template_data : dict, optional
        Extra data the template needs (e.g. reset_url, ticket_id).
    email_type : str
        "html" or "text".  Defaults to "html".

    Returns
    -------
    dict with keys:
        success (bool)  — True if n8n accepted the payload (2xx response).
        error   (str|None) — Human-readable error message on failure.
    """
    # --- local pre-flight validation ----------------------------------------
    if not _is_valid_email(to):
        logger.warning("email_service: invalid recipient address (redacted)")
        return {"success": False, "error": "Invalid recipient email address."}

    if template not in SUPPORTED_TEMPLATES:
        logger.warning("email_service: unsupported template '%s'", template)
        return {"success": False, "error": f"Unsupported email template: {template}"}

    webhook_url = settings.N8N_EMAIL_WEBHOOK_URL
    secret = settings.N8N_EMAIL_WEBHOOK_SECRET

    if not webhook_url or not secret:
        logger.warning(
            "email_service: N8N_EMAIL_WEBHOOK_URL or N8N_EMAIL_WEBHOOK_SECRET not configured — "
            "email dispatch skipped."
        )
        return {"success": False, "error": "Email service not configured."}

    # --- build payload (matches verified n8n payload contract) ---------------
    payload: dict[str, Any] = {
        "to": to,
        "template": template,
        "email_type": email_type,
        "sender_name": sender_name or settings.EMAIL_SENDER_NAME,
    }
    if recipient_name:
        payload["recipient_name"] = recipient_name
    if reply_to and _is_valid_email(reply_to):
        payload["reply_to"] = reply_to
    if template_data:
        # Sanitise: only plain JSON-serialisable values, no nested callables
        payload["template_data"] = {
            k: v for k, v in template_data.items()
            if isinstance(v, (str, int, float, bool, type(None)))
        }

    # --- dispatch -------------------------------------------------------------
    try:
        async with httpx.AsyncClient(timeout=settings.EMAIL_TIMEOUT_SECONDS) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={
                    "X-Helpdesk-Secret": secret,
                    "Content-Type": "application/json",
                    "User-Agent": "SmartHelpdesk/1.0",
                },
            )

        if response.is_success:
            logger.info("email_service: template='%s' dispatched OK (status %d)", template, response.status_code)
            return {"success": True, "error": None}

        # 4xx/5xx — log sanitised error (no payload/secret in log)
        logger.warning(
            "email_service: template='%s' rejected by n8n — HTTP %d",
            template,
            response.status_code,
        )
        return {
            "success": False,
            "error": f"n8n returned HTTP {response.status_code}.",
        }

    except httpx.TimeoutException:
        logger.warning("email_service: template='%s' timed out after %ds", template, settings.EMAIL_TIMEOUT_SECONDS)
        return {"success": False, "error": "Email service request timed out."}

    except httpx.RequestError as exc:
        # Network-level error — log type only, not the exc message (may contain URL)
        logger.warning("email_service: template='%s' network error (%s)", template, type(exc).__name__)
        return {"success": False, "error": "Email service network error."}

    except Exception as exc:  # noqa: BLE001
        logger.error("email_service: unexpected error for template='%s': %s", template, type(exc).__name__)
        return {"success": False, "error": "Unexpected email service error."}


def dispatch_email_sync(
    to: str,
    template: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Synchronous wrapper for dispatch_email.
    Use this ONLY when you cannot use BackgroundTasks (rare cases).
    Prefer BackgroundTasks for all FastAPI route usage.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are inside an already-running event loop (e.g. during tests)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, dispatch_email(to, template, **kwargs))
                return future.result(timeout=settings.EMAIL_TIMEOUT_SECONDS + 2)
        return loop.run_until_complete(dispatch_email(to, template, **kwargs))
    except Exception as exc:  # noqa: BLE001
        logger.error("email_service(sync): error — %s", type(exc).__name__)
        return {"success": False, "error": "Sync email dispatch error."}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_email(addr: str) -> bool:
    if not addr or len(addr) > 254:
        return False
    return bool(_EMAIL_RE.match(addr.strip()))
