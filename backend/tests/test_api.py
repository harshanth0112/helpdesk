from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/health"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Smart IT Helpdesk API" in data["service"]


def test_api_v1_endpoint():
    response = client.get("/api/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"


def test_database_health_check_disconnected_or_connected():
    # Calling the endpoint directly tests the safe exception handling of get_db
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "PostgreSQL"
    assert data["status"] in ("connected", "disconnected")
