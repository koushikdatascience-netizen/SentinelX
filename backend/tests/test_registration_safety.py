import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.workspace_store import init_db


def test_registration_gate_and_existing_login(monkeypatch):
    init_db()
    monkeypatch.setenv("JWT_SECRET", "registration-test-secret-at-least-32-characters")
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "false")
    email = f"invited-{uuid.uuid4()}@example.org"
    body = {"email": email, "password": "StrongPassword123"}
    with TestClient(app) as client:
        monkeypatch.delenv("REGISTRATION_ALLOWED_EMAILS", raising=False)
        assert client.post("/api/v1/auth/register", json=body).status_code == 403
        monkeypatch.setenv("REGISTRATION_ALLOWED_EMAILS", f" {email.upper()} , other@example.org ")
        assert client.post("/api/v1/auth/register", json=body).status_code == 201
        stranger = {**body, "email": f"stranger-{uuid.uuid4()}@example.org"}
        assert client.post("/api/v1/auth/register", json=stranger).status_code == 403
        monkeypatch.setenv("REGISTRATION_ALLOWED_EMAILS", "")
        assert client.post("/api/v1/auth/login", json=body).status_code == 200


def test_unicode_password_bcrypt_limit_is_validation_error():
    with TestClient(app) as client:
        body = {"email": "unicode@example.org", "password": "\u00e9" * 37}
        for endpoint in ("register", "login"):
            assert client.post(f"/api/v1/auth/{endpoint}", json=body).status_code == 422
