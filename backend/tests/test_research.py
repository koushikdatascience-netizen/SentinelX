import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents import build_plan
from app.research import validate_public_url

client = TestClient(app)

def test_plan_requires_approval():
    plan = build_plan({"evidence_source":"https://example.com","title":"Example","text":"Sample store sells chairs"},"Get leads")
    assert plan.source_url == "https://example.com"
    assert len(plan.actions) == 3
    assert all(action.approval_required and action.status == "proposed" for action in plan.actions)

def test_localhost_rejected():
    with pytest.raises(ValueError):
        validate_public_url("http://localhost/admin")

def test_credentials_rejected():
    with pytest.raises(ValueError):
        validate_public_url("https://user:pass@example.com/")

def test_research_endpoint_with_stub(monkeypatch):
    monkeypatch.setenv("ENABLE_LEGACY_ENDPOINTS","true")
    monkeypatch.setattr("app.research.snapshot",lambda url: {"evidence_source":url,"title":"Retailer","text":"Shoes and offers"})
    response = client.post("/api/v1/research",json={"website":"https://example.com","goal":"Improve local customer inquiries"})
    assert response.status_code == 200
    assert response.json()["status"] == "proposed"
    assert response.json()["plan"]["source_title"] == "Retailer"
    assert response.json()["plan"]["actions"][0]["approval_required"]
