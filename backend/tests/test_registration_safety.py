import uuid
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.main import app
from app.workspace_store import LoginAttempt, SessionLocal, init_db


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


def test_login_throttle_is_persistent_and_expires(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "login-throttle-test-secret-at-least-32-characters")
    monkeypatch.setenv("AUTH_LOGIN_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("AUTH_LOGIN_WINDOW_SECONDS", "300")
    email=f"throttle-{uuid.uuid4()}@example.org"
    key=hashlib.sha256(email.lower().encode()).hexdigest()
    credentials={"email":email,"password":"StrongPassword123"}
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/register",json=credentials).status_code==201
        for _ in range(2):
            assert client.post("/api/v1/auth/login",json={**credentials,"password":"WrongPassword123"}).status_code==401
        locked=client.post("/api/v1/auth/login",json={**credentials,"password":"WrongPassword123"})
        assert locked.status_code==429 and int(locked.headers["Retry-After"])>0
        assert client.post("/api/v1/auth/login",json=credentials).status_code==429
        with SessionLocal.begin() as db:
            row=db.get(LoginAttempt,key)
            assert row is not None
            db.execute(update(LoginAttempt).where(LoginAttempt.email_key==key).values(
                window_started_at=datetime.now(timezone.utc)-timedelta(seconds=301),
                locked_until=datetime.now(timezone.utc)-timedelta(seconds=1)))
        assert client.post("/api/v1/auth/login",json=credentials).status_code==200
        with SessionLocal() as db:
            assert db.get(LoginAttempt,key) is None
