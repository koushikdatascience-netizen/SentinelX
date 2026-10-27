from fastapi.testclient import TestClient
from app.main import app
def test_catalog():
    r=TestClient(app).get("/api/v1/models")
    assert r.status_code==200
    assert len(r.json()["models"])==7
def test_preview_requires_auth():
    assert TestClient(app).post("/api/v1/workflows/preview",json={"website":"https://example.com","goal":"Improve customer conversion"}).status_code==401
def test_workflow_preview_safe(authenticated_client):
    r=authenticated_client.post("/api/v1/workflows/preview",json={"website":"https://example.com","goal":"Improve customer conversion through a better storefront"})
    assert r.status_code==200,r.text
    assert r.json()["actual_external_actions"]==0
    assert len(r.json()["steps"])==7
def test_preview_validation(authenticated_client):
    assert authenticated_client.post("/api/v1/workflows/preview",json={"website":"not-an-url","goal":"short"}).status_code==422
