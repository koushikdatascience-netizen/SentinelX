from fastapi.testclient import TestClient
from app.main import app
from app.workflows import ActionStore, State

client = TestClient(app)

def test_review_lifecycle(monkeypatch):
    monkeypatch.setenv('ENABLE_LEGACY_ENDPOINTS','true')
    response = client.post("/api/v1/actions",json={"run_id":"demo-1","kind":"seo","description":"Propose better copy for the landing page","source_url":"https://example.com/"})
    assert response.status_code == 201
    aid = response.json()["id"]
    assert response.json()["state"] == "proposed"
    assert client.get(f"/api/v1/actions/{aid}").status_code == 200
    approved = client.post(f"/api/v1/actions/{aid}/review",json={"decision":"approved"})
    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"
    assert client.post(f"/api/v1/actions/{aid}/review",json={"decision":"rejected"}).status_code == 409

def test_no_arbitrary_transition():
    store = ActionStore()
    rec = store.propose("r","creative","Draft test poster","https://example.com")
    try:
        store.decide(rec.id,State.proposed)
    except ValueError:
        pass
    else:
        raise AssertionError("proposed is not a review decision")
    assert store.get(rec.id).state == State.proposed

def test_unknown_action(monkeypatch):
    monkeypatch.setenv('ENABLE_LEGACY_ENDPOINTS','true')
    assert client.get("/api/v1/actions/missing").status_code == 404
    assert client.post("/api/v1/actions/missing/review",json={"decision":"approved"}).status_code == 404
