from fastapi.testclient import TestClient
from app.main import app
def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code==200
    assert response.json()["database"]=="ok"
    assert response.json()["release"]=="unknown"
def test_health_includes_release(monkeypatch):
    monkeypatch.setenv("SENTINELX_RELEASE","0123456789abcdef0123456789abcdef01234567")
    response = TestClient(app).get("/health")
    assert response.status_code==200
    assert response.json()["release"]=="0123456789abcdef0123456789abcdef01234567"
def test_public_status_labels_unverified_capabilities_as_sample(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true")
    monkeypatch.setenv("MODEL_API_KEY","test-only")
    monkeypatch.setenv("META_VERIFIED_CAPABILITIES","")
    response=TestClient(app).get("/api/v1/status")
    assert response.status_code==200
    data=response.json()
    assert data["capabilities"]["text"]=={"provenance":"sample","live_verified":False}
    assert data["capabilities"]["image"]=={"provenance":"sample","live_verified":False}
    assert data["capabilities"]["vision"]=={"provenance":"sample","live_verified":False}
    assert data["capabilities"]["segment"]["supported"] is False
    assert data["mode"]=="demo"
def test_public_status_reports_only_explicitly_verified_live_capabilities(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true")
    monkeypatch.setenv("MODEL_API_KEY","test-only")
    monkeypatch.setenv("META_VERIFIED_CAPABILITIES","text")
    data=TestClient(app).get("/api/v1/status").json()
    assert data["mode"]=="live"
    assert data["capabilities"]["text"]=={"provenance":"live_meta","live_verified":True}
    assert data["capabilities"]["vision"]=={"provenance":"sample","live_verified":False}
def test_reject_anonymous():
    assert TestClient(app).post("/api/v1/analyze",json={"website":"https://example.com","goal":"Increase leads to business"}).status_code==401
def test_demo(authenticated_client,monkeypatch):
    monkeypatch.setenv("SENTINELX_MODE","demo")
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    r=authenticated_client.post("/api/v1/analyze",json={"website":"https://example.com","goal":"Increase local qualified customer leads"})
    assert r.status_code==200,r.text
    assert r.json()["mode"]=="demo"
    assert r.json()["requires_approval"] is True
def test_invalid(authenticated_client,monkeypatch):
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    assert authenticated_client.post("/api/v1/analyze",json={"website":"not-a-url","goal":"short"}).status_code==422
