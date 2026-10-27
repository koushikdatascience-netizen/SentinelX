from fastapi.testclient import TestClient
from app.main import app
from app.workflows import ActionStore,State
def test_auth_required():
    assert TestClient(app).post("/api/v1/actions",json={"run_id":"demo","kind":"seo","description":"Improve a business homepage","source_url":"https://example.com"}).status_code==401
def test_review_lifecycle(authenticated_client,monkeypatch):
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    client=authenticated_client
    r=client.post("/api/v1/actions",json={"run_id":"demo-1","kind":"seo","description":"Propose better copy for the landing page","source_url":"https://example.com/"})
    assert r.status_code==201,r.text
    aid=r.json()["id"]
    assert client.get(f"/api/v1/actions/{aid}").status_code==200
    assert client.post(f"/api/v1/actions/{aid}/review",json={"decision":"approved"}).json()["state"]=="approved"
    assert client.post(f"/api/v1/actions/{aid}/review",json={"decision":"rejected"}).status_code==409
def test_no_arbitrary_transition():
    store=ActionStore()
    rec=store.propose("r","creative","Draft test poster","https://example.com")
    try: store.decide(rec.id,State.proposed)
    except ValueError: pass
    else: raise AssertionError("invalid transition allowed")
    assert store.get(rec.id).state==State.proposed
def test_unknown_action(authenticated_client,monkeypatch):
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    assert authenticated_client.get("/api/v1/actions/missing").status_code==404
    assert authenticated_client.post("/api/v1/actions/missing/review",json={"decision":"approved"}).status_code==404
