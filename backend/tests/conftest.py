import os
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import init_db

@pytest.fixture
def authenticated_client():
    os.environ.setdefault("JWT_SECRET","test-secret-for-backend-suite-at-least-32-characters")
    init_db()
    with TestClient(app) as client:
        email="fixture-"+str(uuid.uuid4())+"@example.org"
        assert client.post("/api/v1/auth/register",json={"email":email,"password":"StrongPassword123"}).status_code==201
        login=client.post("/api/v1/auth/login",json={"email":email,"password":"StrongPassword123"})
        assert login.status_code==200
        client.headers.update({"Authorization":"Bearer "+login.json()["access_token"]})
        yield client
