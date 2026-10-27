"""Offline provider fixtures only. Never use real credentials or network calls."""
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from app import providers
from scripts import meta_smoke


def response(text="OK", reason="stop", choices=True):
    return NS(
        choices=[NS(message=NS(content=text), finish_reason=reason)] if choices else [],
        usage=NS(prompt_tokens=10, completion_tokens=40,
                 completion_tokens_details=NS(reasoning_tokens=38)),
    )


def fake_client(monkeypatch, module, result):
    create = Mock(return_value=result)
    constructor = Mock(return_value=NS(chat=NS(completions=NS(create=create))))
    monkeypatch.setattr(module, "OpenAI", constructor)
    return constructor, create


@pytest.mark.parametrize("text,reason,choices", [
    ("", "length", True), ("  ", "stop", True),
    (None, "content_filter", True), ("Partial", "length", True),
    ("", "stop", False),
])
def test_smoke_incomplete_response_fails_without_retry(monkeypatch, capsys, text, reason, choices):
    monkeypatch.setenv("MODEL_API_KEY", "test-secret-do-not-log")
    monkeypatch.setenv("META_SMOKE_ACK", "I_ACKNOWLEDGE_ONE_PAID_REQUEST")
    constructor, create = fake_client(monkeypatch, meta_smoke, response(text, reason, choices))
    assert meta_smoke.main() == 1
    create.assert_called_once()
    assert constructor.call_args.kwargs["max_retries"] == 0
    output = capsys.readouterr()
    assert "test-secret-do-not-log" not in output.out + output.err
    assert "Smoke test succeeded" not in output.out
    assert "Reasoning tokens: 38" in output.out


def test_smoke_minimal_bounded_request(monkeypatch, capsys):
    monkeypatch.setenv("MODEL_API_KEY", "test-only")
    monkeypatch.setenv("META_SMOKE_ACK", "I_ACKNOWLEDGE_ONE_PAID_REQUEST")
    _, create = fake_client(monkeypatch, meta_smoke, response())
    assert meta_smoke.main() == 0
    assert create.call_args.kwargs["reasoning_effort"] == "minimal"
    assert create.call_args.kwargs["max_completion_tokens"] == 128
    assert "Expected OK received: True" in capsys.readouterr().out


def test_smoke_requires_explicit_ack_before_client_creation(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-only")
    monkeypatch.delenv("META_SMOKE_ACK", raising=False)
    constructor, _ = fake_client(monkeypatch, meta_smoke, response())
    assert meta_smoke.main() == 2
    constructor.assert_not_called()


@pytest.mark.parametrize("text,reason", [("", "length"), ("Partial", "length")])
def test_app_rejects_empty_or_truncated_answers_without_retry(monkeypatch, text, reason):
    from app import budget
    monkeypatch.setattr(providers, "configured_provider", lambda: providers.ProviderConfig(
        "meta", "https://api.meta.ai/v1", "muse-spark-1.3", "test-only"))
    reserve = Mock()
    monkeypatch.setattr(budget, "reserve", reserve)
    _, create = fake_client(monkeypatch, providers, response(text, reason))
    with pytest.raises(ValueError, match="No retry made"):
        providers.infer("Test input")
    create.assert_called_once()
    reserve.assert_called_once_with("meta", 5)


def test_app_reports_usage_and_uses_minimal_reasoning(monkeypatch):
    from app import budget
    monkeypatch.setattr(providers, "configured_provider", lambda: providers.ProviderConfig(
        "meta", "https://api.meta.ai/v1", "muse-spark-1.3", "test-only"))
    monkeypatch.setattr(budget, "reserve", Mock())
    _, create = fake_client(monkeypatch, providers, response())
    result = providers.infer("Test input")
    assert result["status"] == "completed"
    assert result["usage"]["reasoning_tokens"] == 38
    assert create.call_args.kwargs["reasoning_effort"] == "minimal"
    assert create.call_args.kwargs["max_completion_tokens"] == 500
