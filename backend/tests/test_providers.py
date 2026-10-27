import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.providers import configured_provider, infer

def test_demo_mode(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    assert infer("Find risks for this plan")["status"]=="simulated"

def test_free_openrouter(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY","fake")
    monkeypatch.setenv("INFERENCE_MODEL","openrouter/example:free")
    assert configured_provider().name=="openrouter"

def test_block_paid_models(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY","fake")
    monkeypatch.setenv("INFERENCE_MODEL","example/paid")
    monkeypatch.delenv("ALLOW_PAID_INFERENCE",raising=False)
    with pytest.raises(ValueError,match="free"):
        configured_provider()

def test_missing_key(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","groq")
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    with pytest.raises(ValueError,match="GROQ_API_KEY"):
        configured_provider()

def test_auth_required():
    assert TestClient(app).get("/api/v1/inference/status").status_code==401

def test_demo_endpoint(monkeypatch,authenticated_client):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    client=authenticated_client
    wid=client.post("/api/v1/workspaces",json={"name":"Inference test"}).json()["id"]
    run=client.post(f"/api/v1/workspaces/{wid}/runs",json={
        "website":"https://example.com","goal":"Review our business model"}).json()
    result=client.post("/api/v1/inference/test",json={"workspace_id":wid,"run_id":run["id"],
        "prompt":"Review our business model"})
    assert result.status_code==200 and result.json()["status"]=="simulated"

def test_local_ollama_adapter_requires_no_paid_key(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","ollama")
    monkeypatch.setenv("INFERENCE_MODEL","llama3.2:3b")
    monkeypatch.delenv("ALLOW_PAID_INFERENCE",raising=False)
    config=configured_provider()
    assert config.name=="ollama"
    assert config.model=="llama3.2:3b"
    assert config.api_key=="ollama"
