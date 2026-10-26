import os
os.environ.setdefault("JWT_SECRET","test-secret-for-backend-suite-at-least-32-characters")
from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import init_db

def test_workspace_isolation():
    init_db()
    with TestClient(app) as client:
        def register(email):
            r=client.post("/api/v1/auth/register",json={"email":email,"password":"StrongPassword123"})
            assert r.status_code in (201,409),r.text
            r=client.post("/api/v1/auth/login",json={"email":email,"password":"StrongPassword123"})
            assert r.status_code==200,r.text
            return {"Authorization":"Bearer "+r.json()["access_token"]}
        import uuid
        a=register(str(uuid.uuid4())+"@example.org")
        b=register(str(uuid.uuid4())+"@example.org")
        assert client.get("/api/v1/workspaces").status_code==401
        res=client.post("/api/v1/workspaces",json={"name":"My Retailer"},headers=a)
        assert res.status_code==201,res.text
        wid=res.json()["id"]
        assert client.get(f"/api/v1/workspaces/{wid}/runs",headers=b).status_code==404
        run=client.post(f"/api/v1/workspaces/{wid}/runs",json={"website":"https://example.com","goal":"Improve qualified leads from the website"},headers=a)
        assert run.status_code==201,run.text
        assert run.json()["result"]["mode"]=="mock"
        assert client.get(f"/api/v1/workspaces/{wid}/runs",headers=b).status_code==404
        assert len(client.get(f"/api/v1/workspaces/{wid}/runs",headers=a).json())>=1
