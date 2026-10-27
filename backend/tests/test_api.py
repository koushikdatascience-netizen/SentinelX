from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import MetaCapabilityCheck, SessionLocal, utcnow
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
    monkeypatch.setenv("SENTINELX_MODE","live")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true")
    monkeypatch.setenv("MODEL_API_KEY","test-only")
    monkeypatch.setenv("META_VERIFIED_CAPABILITIES","")
    response=TestClient(app).get("/api/v1/status")
    assert response.status_code==200
    data=response.json()
    assert data["capabilities"]["text"]["state"]=="SAMPLE"
    assert data["capabilities"]["image"]["state"]=="SAMPLE"
    assert data["capabilities"]["vision"]["state"]=="SAMPLE"
    assert data["capabilities"]["text"]["last_success_at"] is None
    assert data["automatic_publishing"] is False
def test_public_status_reports_only_explicitly_verified_live_capabilities(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    monkeypatch.setenv("SENTINELX_MODE","live")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true")
    monkeypatch.setenv("MODEL_API_KEY","test-only")
    with SessionLocal.begin() as db:
        db.merge(MetaCapabilityCheck(capability="text",model="muse-spark-1.3",succeeded_at=utcnow()))
    data=TestClient(app).get("/api/v1/status").json()
    assert data["capabilities"]["text"]["state"]=="LIVE"
    assert data["capabilities"]["vision"]["state"]=="SAMPLE"
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
