from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_catalog():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 7
    assert all(model["access"] in ("mock_only", "configured_not_verified") for model in data["models"])

def test_workflow_preview_safe():
    response = client.post("/api/v1/workflows/preview",json={
        "website":"https://example.com",
        "goal":"Improve customer conversion through a better storefront"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["actual_external_actions"] == 0
    assert data["mode"] == "mock"
    assert len(data["steps"]) == 7
    assert data["approvals_needed"]

def test_preview_input_validation():
    response = client.post("/api/v1/workflows/preview",json={
        "website":"not-an-url","goal":"short"
    })
    assert response.status_code == 422
