"""Free inference gates: never silently switch to a paid model."""
import pytest
from app.providers import infer, configured_provider

def test_openrouter_free_disabled_by_default(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY","test-key")
    monkeypatch.setenv("INFERENCE_MODEL","vendor/example:free")
    monkeypatch.delenv("ENABLE_OPENROUTER_FREE",raising=False)
    with pytest.raises(ValueError,match="disabled"):
        infer("Summarize the owner's supplied evidence for conversion improvements.")

def test_openrouter_paid_model_not_allowed(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY","test-key")
    monkeypatch.setenv("INFERENCE_MODEL","vendor/expensive-model")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_OPENROUTER_FREE","true")
    with pytest.raises(ValueError,match="Only OpenRouter :free"):
        infer("Summarize the owner's supplied evidence for conversion improvements.")

def test_free_provider_needs_owned_run(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY","test-key")
    monkeypatch.setenv("INFERENCE_MODEL","vendor/example:free")
    monkeypatch.setenv("ENABLE_OPENROUTER_FREE","true")
    with pytest.raises(ValueError,match="Owned persisted workflow"):
        infer("Summarize the owner's supplied evidence for conversion improvements.")

def test_no_key_never_makes_external_call(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY",raising=False)
    monkeypatch.setenv("INFERENCE_MODEL","vendor/example:free")
    monkeypatch.setenv("ENABLE_OPENROUTER_FREE","true")
    with pytest.raises(ValueError,match="OPENROUTER_API_KEY"):
        configured_provider()
