"""
backend/tests/test_auth.py — Comprehensive Phase 4 auth test suite.

All tests run against an in-memory SQLite database via the get_db dependency
override — no live PostgreSQL connection required.

Test coverage:
  1.  test_register_success
  2.  test_register_duplicate_email
  3.  test_register_invalid_password_too_short
  4.  test_register_invalid_password_no_digit
  5.  test_register_cannot_set_admin_role (role field ignored/rejected at schema level)
  6.  test_login_valid
  7.  test_login_invalid_password
  8.  test_login_nonexistent_user
  9.  test_expired_jwt
  10. test_invalid_jwt_signature
  11. test_refresh_token_rotation
  12. test_refresh_token_reuse_detection
  13. test_logout_revocation
  14. test_me_endpoint_authenticated
  15. test_me_endpoint_unauthenticated
  16. test_account_inactive_login
  17. test_forgot_password_registered_email
  18. test_forgot_password_unknown_email  (anti-enumeration: same 200 response)
  19. test_reset_password_success
  20. test_reset_password_invalid_token
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import event

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models import User
from app.core.security import (
    generate_jwt_access_token,
    get_password_hash,
    hash_token,
    generate_secure_token,
)
from app.models.refresh_token import RefreshToken

# ---------------------------------------------------------------------------
# SQLite in-memory engine — shared across all tests in this module
# ---------------------------------------------------------------------------

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)

# SQLite doesn't enforce FK by default; enable it so cascade tests are correct.
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="module", autouse=True)
def create_tables():
    """Create all tables once for the module, drop them when done."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """Provide a transactional session that is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    """TestClient with get_db overridden to use the per-test SQLite session.

    Rate limiting is disabled in tests by replacing the app-level limiter
    with a fresh MemoryStorage instance before each test, ensuring no
    cross-test carry-over of request counts.
    """
    from limits.storage import MemoryStorage
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    # Reset rate limit counters by installing a fresh in-memory storage
    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # rollback handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        c.db_session = db_session
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "Secure123",
    "first_name": "Alice",
    "last_name": "Smith",
}


def _register_user(client: TestClient, email: str = "alice@example.com", approve: bool = True) -> dict:
    """Register a user and optionally approve them in DB for login/token tests."""
    r = client.post("/api/v1/auth/register", json={**VALID_REGISTER_PAYLOAD, "email": email})
    assert r.status_code == 201, r.text
    if approve and hasattr(client, "db_session"):
        user = client.db_session.query(User).filter(User.email == email.lower()).first()
        user.approval_status = "approved"
        client.db_session.commit()
    return r.json()


def _login(client: TestClient, email: str = "alice@example.com", password: str = "Secure123") -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


# ===========================================================================
# 1. Registration tests
# ===========================================================================

class TestRegistration:
    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json=VALID_REGISTER_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == "alice@example.com"
        assert body["role"] == "employee"
        assert "password_hash" not in body
        assert "failed_login_attempts" not in body

    def test_register_duplicate_email(self, client):
        client.post("/api/v1/auth/register", json=VALID_REGISTER_PAYLOAD)
        r = client.post("/api/v1/auth/register", json=VALID_REGISTER_PAYLOAD)
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"].lower()

    def test_register_invalid_password_too_short(self, client):
        payload = {**VALID_REGISTER_PAYLOAD, "email": "b@b.com", "password": "Ab1"}
        r = client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 422

    def test_register_invalid_password_no_digit(self, client):
        payload = {**VALID_REGISTER_PAYLOAD, "email": "c@c.com", "password": "NoDigitsHere"}
        r = client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 422

    def test_register_cannot_set_admin_role(self, client):
        """
        The RegisterRequest schema has no 'role' field.
        Any role field sent in JSON is silently ignored (Pydantic extra='ignore'
        equivalent — Pydantic V2 forbids unknown fields by default on BaseModel,
        but we don't declare 'role' at all, so the validator never runs it).
        The created user must always be 'employee'.
        """
        payload = {**VALID_REGISTER_PAYLOAD, "email": "d@d.com", "role": "admin"}
        r = client.post("/api/v1/auth/register", json=payload)
        # Either 201 (role silently dropped) or 422 (extra field rejected).
        # Either is acceptable — what's NOT acceptable is role='admin' being stored.
        if r.status_code == 201:
            assert r.json()["role"] == "employee"
        else:
            assert r.status_code == 422


# ===========================================================================
# 2. Login tests
# ===========================================================================

class TestLogin:
    def test_login_valid(self, client):
        _register_user(client)
        r = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "Secure123"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_invalid_password(self, client):
        _register_user(client)
        r = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "Wrong999"})
        assert r.status_code == 401
        # Generic message — no "wrong password" revelation
        assert "password" not in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Any1234"})
        assert r.status_code == 401

    def test_account_inactive_login(self, client, db_session: Session):
        """Suspended/inactive user is rejected with 403 after credential verification."""
        _register_user(client, email="inactive@example.com")
        # Deactivate directly in DB
        user = db_session.query(User).filter(User.email == "inactive@example.com").first()
        user.is_active = False
        user.approval_status = "suspended"
        db_session.commit()

        r = client.post("/api/v1/auth/login", json={"email": "inactive@example.com", "password": "Secure123"})
        assert r.status_code == 403
        assert "suspended" in r.json()["detail"].lower()


# ===========================================================================
# 3. JWT tests
# ===========================================================================

class TestJWT:
    def test_expired_jwt(self, client):
        _register_user(client)
        expired_token = generate_jwt_access_token(
            data={"sub": "1", "role": "employee"},
            expires_delta=timedelta(seconds=-1),
        )
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert r.status_code == 401

    def test_invalid_jwt_signature(self, client):
        _register_user(client)
        tampered = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.invalid_signature"
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert r.status_code == 401


# ===========================================================================
# 4. Refresh-token lifecycle
# ===========================================================================

class TestRefreshToken:
    def test_refresh_token_rotation(self, client):
        _register_user(client)
        tokens = _login(client)

        r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        new_tokens = r.json()
        assert "access_token" in new_tokens
        assert new_tokens["refresh_token"] != tokens["refresh_token"]  # new token issued

    def test_refresh_token_reuse_detection(self, client):
        """Using a refresh token twice triggers reuse detection (all tokens revoked)."""
        _register_user(client)
        tokens = _login(client)
        old_refresh = tokens["refresh_token"]

        # First use — legitimate rotation
        r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert r1.status_code == 200

        # Second use of the same (now-revoked) token — reuse detected
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert r2.status_code == 401


# ===========================================================================
# 5. Logout
# ===========================================================================

class TestLogout:
    def test_logout_revocation(self, client):
        _register_user(client)
        tokens = _login(client)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Logout
        r = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r.status_code == 204

        # Revoked refresh token should no longer work
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r2.status_code == 401


# ===========================================================================
# 6. /me endpoint
# ===========================================================================

class TestMeEndpoint:
    def test_me_endpoint_authenticated(self, client):
        _register_user(client)
        tokens = _login(client)
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "alice@example.com"
        assert body["role"] == "employee"
        assert "password_hash" not in body
        assert "failed_login_attempts" not in body

    def test_me_endpoint_unauthenticated(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401


# ===========================================================================
# 7. Password reset
# ===========================================================================

class TestPasswordReset:
    def test_forgot_password_registered_email(self, client):
        _register_user(client, email="reset@example.com")
        r = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
        assert r.status_code == 200
        body = r.json()
        assert "message" in body
        # Phase 4 testing convenience — raw token returned
        assert "reset_token" in body

    def test_forgot_password_unknown_email(self, client):
        """Anti-enumeration: same 200 response even for unknown emails."""
        r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
        assert r.status_code == 200
        body = r.json()
        assert "message" in body
        # No reset_token for unregistered email
        assert "reset_token" not in body

    def test_reset_password_success(self, client):
        _register_user(client, email="resetme@example.com")
        # Get reset token
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "resetme@example.com"})
        raw_token = resp.json()["reset_token"]

        # Reset password
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass456"},
        )
        assert r.status_code == 200

        # Old password no longer works
        r_old = client.post("/api/v1/auth/login", json={"email": "resetme@example.com", "password": "Secure123"})
        assert r_old.status_code == 401

        # New password works
        r_new = client.post("/api/v1/auth/login", json={"email": "resetme@example.com", "password": "NewPass456"})
        assert r_new.status_code == 200

    def test_reset_password_invalid_token(self, client):
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "completely-fake-token-xyz", "new_password": "NewPass456"},
        )
        assert r.status_code == 400
