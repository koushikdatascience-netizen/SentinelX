import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents import build_plan
from app.research import validate_public_url
def test_plan_requires_approval():
    plan=build_plan({"evidence_source":"https://example.com","title":"Example","text":"Sample store sells chairs"},"Get leads")
    assert len(plan.actions)==3
    assert all(x.approval_required and x.status=="proposed" for x in plan.actions)
def test_localhost_rejected():
    with pytest.raises(ValueError): validate_public_url("http://localhost/admin")
def test_credentials_rejected():
    with pytest.raises(ValueError): validate_public_url("https://user:pass@example.com/")
def test_research_auth_required():
    assert TestClient(app).post("/api/v1/research",json={"website":"https://example.com","goal":"Improve customer inquiries"}).status_code==401
def test_research_stub(monkeypatch,authenticated_client):
    monkeypatch.setattr("app.research.snapshot",lambda url:{"evidence_source":url,"title":"Retailer","text":"Shoes and offers"})
    r=authenticated_client.post("/api/v1/research",json={"website":"https://example.com","goal":"Improve local customer inquiries"})
    assert r.status_code==200,r.text
    assert r.json()["status"]=="proposed"
