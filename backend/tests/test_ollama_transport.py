import pytest
from app.providers import infer

def test_ollama_disabled_by_default(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","ollama")
    monkeypatch.setenv("INFERENCE_MODEL","llama3.2:3b")
    monkeypatch.delenv("ENABLE_OLLAMA_INFERENCE",raising=False)
    with pytest.raises(ValueError,match="disabled"):
        infer("Analyze these customer service goals")

def test_ollama_live_transport_is_explicit_and_attributed(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","ollama")
    monkeypatch.setenv("INFERENCE_MODEL","llama3.2:3b")
    monkeypatch.setenv("ENABLE_OLLAMA_INFERENCE","true")
    monkeypatch.setenv("OLLAMA_OPENAI_BASE_URL","http://127.0.0.1:11434/v1")
    seen={}
    class Message:
        content="Suggested action: add a clear quote request. This is a hypothesis."
    class Choice:
        message=Message()
    class Answer:
        choices=[Choice()]
    class Completions:
        @staticmethod
        def create(**kwargs):
            seen.update(kwargs)
            return Answer()
    class Chat:
        completions=Completions()
    class FakeClient:
        chat=Chat()
    monkeypatch.setattr("openai.OpenAI",lambda **kwargs:FakeClient())
    result=infer("Review this business website URL without fetching")
    assert result["status"]=="completed"
    assert result["provenance"]=="live_ollama"
    assert result["provider"]=="ollama"
    assert result["model"]=="llama3.2:3b"
    assert "hypothesis" in result["text"]
    assert seen["max_tokens"]==750

def test_ollama_rejects_untrusted_public_endpoint(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","ollama")
    monkeypatch.setenv("INFERENCE_MODEL","llama3.2:3b")
    monkeypatch.setenv("ENABLE_OLLAMA_INFERENCE","true")
    monkeypatch.setenv("OLLAMA_OPENAI_BASE_URL","https://example.com/v1")
    with pytest.raises(ValueError,match="localhost"):
        infer("Review this business and its research goals")
