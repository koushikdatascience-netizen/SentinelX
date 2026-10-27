import uuid
from datetime import datetime,timedelta,timezone
from fastapi.testclient import TestClient
from sqlalchemy import update
from app.main import app
from app.workspace_store import DemoSession, SessionLocal

def unique_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET","guest-test-"+str(uuid.uuid4())+"-sufficiently-long-secret")

def test_guest_session_isolated_and_expires(monkeypatch):
    unique_secret(monkeypatch)
    monkeypatch.setenv("ENABLE_PUBLIC_DEMO_SESSION","true")
    monkeypatch.setenv("DEMO_SESSIONS_PER_IP_HOUR","5")
    with TestClient(app) as c:
        r=c.post("/api/v1/demo/session")
        assert r.status_code==201,r.text
        result=r.json()
        assert result["provenance"]=="sample" and result["paid_calls"]==0
        headers={"Authorization":"Bearer "+result["access_token"]}
        ws=c.get("/api/v1/workspaces",headers=headers)
        assert ws.status_code==200 and ws.json()[0]["id"]==result["workspace"]["id"]
        assert c.post("/api/v1/inference/test",headers=headers,json={"prompt":"Tell me about this business"}).status_code==403
        assert c.post("/api/v1/campaigns",headers=headers,json={
            "workspace_id":result["workspace"]["id"],
            "business_description":"A sample wooden furniture shop with consultations and custom projects.",
            "goal":"Generate more relevant qualified customer inquiries",
            "platforms":["instagram"]}).json()["provenance"]=="sample"
        with SessionLocal.begin() as db:
            db.execute(update(DemoSession).where(DemoSession.user_id.is_not(None))
                .values(expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
        assert c.get("/api/v1/workspaces",headers=headers).status_code==401

def test_guest_session_rate_limit(monkeypatch):
    unique_secret(monkeypatch)
    monkeypatch.setenv("ENABLE_PUBLIC_DEMO_SESSION","true")
    monkeypatch.setenv("DEMO_SESSIONS_PER_IP_HOUR","1")
    with TestClient(app) as c:
        assert c.post("/api/v1/demo/session").status_code==201
        assert c.post("/api/v1/demo/session").status_code==429

def test_demo_off_without_operator_consent(monkeypatch):
    unique_secret(monkeypatch)
    monkeypatch.setenv("ENABLE_PUBLIC_DEMO_SESSION","false")
    with TestClient(app) as c:
        assert c.post("/api/v1/demo/session").status_code==403
