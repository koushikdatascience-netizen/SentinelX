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

def test_demo_endpoint(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    # Verify internal handler independently; authentication checked above.
    from app.inference_routes import test_inference, InferenceRequest
    assert test_inference(InferenceRequest(prompt="Review our business model"),user=object())["status"]=="simulated"
