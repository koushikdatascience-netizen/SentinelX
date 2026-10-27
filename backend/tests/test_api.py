from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").status_code == 200

def test_demo(monkeypatch):
    monkeypatch.setenv("SENTINELX_MODE","demo")
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    response = client.post("/api/v1/analyze",json={"website":"https://example.com","goal":"Increase local qualified customer leads"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demo"
    assert body["requires_approval"] is True
    assert body["findings"][0]["confidence"] == "unverified"

def test_invalid():
    assert client.post("/api/v1/analyze",json={"website":"not-a-url","goal":"short"}).status_code == 422
