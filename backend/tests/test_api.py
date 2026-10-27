from fastapi.testclient import TestClient
from app.main import app
def test_health():
    assert TestClient(app).get("/health").status_code==200
def test_reject_anonymous():
    assert TestClient(app).post("/api/v1/analyze",json={"website":"https://example.com","goal":"Increase leads to business"}).status_code==401
def test_demo(authenticated_client,monkeypatch):
    monkeypatch.setenv("SENTINELX_MODE","demo")
    r=authenticated_client.post("/api/v1/analyze",json={"website":"https://example.com","goal":"Increase local qualified customer leads"})
    assert r.status_code==200,r.text
    assert r.json()["mode"]=="demo"
    assert r.json()["requires_approval"] is True
def test_invalid(authenticated_client):
    assert authenticated_client.post("/api/v1/analyze",json={"website":"not-a-url","goal":"short"}).status_code==422
