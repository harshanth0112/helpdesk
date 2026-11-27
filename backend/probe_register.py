import uuid, traceback
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app, raise_server_exceptions=True)
payload = {
    "email": f"probe_{uuid.uuid4().hex[:8]}@example.com",
    "password": "Passw0rd123",
    "first_name": "Probe",
    "last_name": "User",
}
r = c.post("/api/v1/auth/register", json=payload)
print("STATUS", r.status_code)
print(r.text[:2000])
