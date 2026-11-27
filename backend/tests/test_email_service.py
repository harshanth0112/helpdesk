"""
tests/test_email_service.py — Unit tests for email_service.py

Tests:
  - Valid dispatch (mocked 200 response)
  - Invalid recipient email
  - Unsupported template name
  - Missing webhook configuration
  - n8n HTTP 400 response
  - n8n HTTP 401 response
  - n8n HTTP 502 response
  - Timeout
  - Network error
  - Each of the 6 business email templates
  - No secret in log output
  - No raw token in log output
  - template_data sanitisation (non-serialisable values stripped)
"""

import asyncio
import logging
import pytest
import httpx

from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from app.services.email_service import dispatch_email, _is_valid_email, SUPPORTED_TEMPLATES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.is_success = status_code < 400
    return r


def run(coro):
    """Helper to run coroutines in tests without pytest-asyncio."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# _is_valid_email tests
# ---------------------------------------------------------------------------

class TestIsValidEmail:
    def test_valid_emails(self):
        for addr in ["user@example.com", "a+b@sub.domain.io", "x@x.co"]:
            assert _is_valid_email(addr), addr

    def test_invalid_emails(self):
        for addr in ["", "not-an-email", "@domain.com", "user@", "a" * 255 + "@x.com", None]:
            assert not _is_valid_email(addr or ""), addr  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# dispatch_email — configuration guard
# ---------------------------------------------------------------------------

class TestDispatchEmailConfig:
    def test_missing_webhook_url(self, caplog):
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.N8N_EMAIL_WEBHOOK_URL = ""
            mock_settings.N8N_EMAIL_WEBHOOK_SECRET = "secret"
            mock_settings.EMAIL_SENDER_NAME = "Helpdesk"
            mock_settings.EMAIL_TIMEOUT_SECONDS = 10
            with caplog.at_level(logging.WARNING, logger="app.services.email_service"):
                result = run(dispatch_email("user@example.com", "account_registration"))
        assert result["success"] is False
        assert "not configured" in result["error"]

    def test_missing_secret(self, caplog):
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.N8N_EMAIL_WEBHOOK_URL = "https://example.com/webhook"
            mock_settings.N8N_EMAIL_WEBHOOK_SECRET = ""
            mock_settings.EMAIL_SENDER_NAME = "Helpdesk"
            mock_settings.EMAIL_TIMEOUT_SECONDS = 10
            result = run(dispatch_email("user@example.com", "account_registration"))
        assert result["success"] is False
        assert "not configured" in result["error"]


# ---------------------------------------------------------------------------
# dispatch_email — input validation
# ---------------------------------------------------------------------------

class TestDispatchEmailValidation:
    def test_invalid_recipient(self):
        result = run(dispatch_email("not-an-email", "account_registration"))
        assert result["success"] is False
        assert "Invalid recipient" in result["error"]

    def test_unsupported_template(self):
        result = run(dispatch_email("user@example.com", "not_a_real_template"))
        assert result["success"] is False
        assert "Unsupported" in result["error"]

    def test_template_data_sanitisation(self):
        """Non-serialisable values should be stripped from template_data."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.N8N_EMAIL_WEBHOOK_URL = "https://example.com/webhook"
            mock_settings.N8N_EMAIL_WEBHOOK_SECRET = "secret"
            mock_settings.EMAIL_SENDER_NAME = "Helpdesk"
            mock_settings.EMAIL_TIMEOUT_SECONDS = 10

            sent_payload = {}

            async def fake_post(url, json=None, headers=None):
                sent_payload.update(json or {})
                return _mock_response(200)

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = fake_post

            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                result = run(dispatch_email(
                    "user@example.com",
                    "account_registration",
                    template_data={
                        "valid_str": "hello",
                        "valid_int": 42,
                        "callable_bad": lambda: None,   # should be stripped
                        "list_bad": [1, 2, 3],          # should be stripped
                    },
                ))
        assert result["success"] is True
        td = sent_payload.get("template_data", {})
        assert "valid_str" in td
        assert "valid_int" in td
        assert "callable_bad" not in td
        assert "list_bad" not in td


# ---------------------------------------------------------------------------
# dispatch_email — HTTP response handling
# ---------------------------------------------------------------------------

class TestDispatchEmailHTTP:
    def _make_settings(self):
        m = MagicMock()
        m.N8N_EMAIL_WEBHOOK_URL = "https://n8n.example.com/webhook/helpdesk/send-email"
        m.N8N_EMAIL_WEBHOOK_SECRET = "test-secret-value"
        m.EMAIL_SENDER_NAME = "Smart IT Helpdesk"
        m.EMAIL_TIMEOUT_SECONDS = 10
        return m

    def _run_with_response(self, status_code: int, template="account_registration", **kwargs):
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=_mock_response(status_code))
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                return run(dispatch_email("user@example.com", template, **kwargs))

    def test_success_200(self):
        result = self._run_with_response(200)
        assert result["success"] is True
        assert result["error"] is None

    def test_http_400(self):
        result = self._run_with_response(400)
        assert result["success"] is False
        assert "400" in result["error"]

    def test_http_401(self):
        result = self._run_with_response(401)
        assert result["success"] is False
        assert "401" in result["error"]

    def test_http_502(self):
        result = self._run_with_response(502)
        assert result["success"] is False
        assert "502" in result["error"]

    def test_timeout(self):
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                result = run(dispatch_email("user@example.com", "account_registration"))
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    def test_network_error(self):
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.RequestError("connection refused", request=MagicMock())
            )
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                result = run(dispatch_email("user@example.com", "account_registration"))
        assert result["success"] is False
        assert "network error" in result["error"].lower()

    def test_no_secret_in_logs(self, caplog):
        """Webhook secret must never appear in log output."""
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=_mock_response(401))
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                with caplog.at_level(logging.DEBUG, logger="app.services.email_service"):
                    run(dispatch_email("user@example.com", "account_registration"))
        assert "test-secret-value" not in caplog.text


# ---------------------------------------------------------------------------
# 6 business template dispatches
# ---------------------------------------------------------------------------

class TestBusinessTemplates:
    def _make_settings(self):
        m = MagicMock()
        m.N8N_EMAIL_WEBHOOK_URL = "https://n8n.example.com/webhook/helpdesk/send-email"
        m.N8N_EMAIL_WEBHOOK_SECRET = "s3cr3t"
        m.EMAIL_SENDER_NAME = "Smart IT Helpdesk"
        m.EMAIL_TIMEOUT_SECONDS = 10
        return m

    def _dispatch(self, template, **kwargs):
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=_mock_response(200))
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                return run(dispatch_email("user@example.com", template, **kwargs))

    def test_account_registration(self):
        r = self._dispatch("account_registration", recipient_name="Alice")
        assert r["success"] is True

    def test_account_approval(self):
        r = self._dispatch("account_approval", recipient_name="Bob", template_data={"role": "technician"})
        assert r["success"] is True

    def test_account_rejection(self):
        r = self._dispatch("account_rejection", recipient_name="Carol", template_data={"rejection_reason": "Duplicate"})
        assert r["success"] is True

    def test_ticket_assignment(self):
        r = self._dispatch(
            "ticket_assignment",
            recipient_name="Dave",
            template_data={"ticket_id": "TKT-001", "ticket_title": "VPN Issue", "ticket_priority": "high"},
        )
        assert r["success"] is True

    def test_ticket_status_update(self):
        r = self._dispatch(
            "ticket_status_update",
            recipient_name="Eve",
            template_data={"ticket_id": "TKT-002", "ticket_title": "Email Issue", "new_status": "resolved"},
        )
        assert r["success"] is True

    def test_password_reset(self):
        r = self._dispatch(
            "password_reset",
            template_data={"reset_url": "https://helpdesk.example.com/reset-password?token=abc123"},
        )
        assert r["success"] is True

    def test_no_raw_token_in_logs(self, caplog):
        """Raw reset token value must never be logged."""
        raw = "super-secret-reset-token-abc123"
        with patch("app.services.email_service.settings", self._make_settings()):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=_mock_response(200))
            with patch("app.services.email_service.httpx.AsyncClient", return_value=mock_client):
                with caplog.at_level(logging.DEBUG, logger="app.services.email_service"):
                    run(dispatch_email(
                        "user@example.com",
                        "password_reset",
                        template_data={"reset_url": f"https://app.example.com/reset?token={raw}"},
                    ))
        # The raw token value itself must not appear in logs
        # (the reset_url containing it may appear in payload but not in our logs)
        assert raw not in caplog.text


# ---------------------------------------------------------------------------
# SUPPORTED_TEMPLATES constant
# ---------------------------------------------------------------------------

class TestSupportedTemplates:
    def test_all_six_templates_present(self):
        expected = {
            "account_registration",
            "account_approval",
            "account_rejection",
            "ticket_assignment",
            "ticket_status_update",
            "password_reset",
        }
        assert expected == SUPPORTED_TEMPLATES
