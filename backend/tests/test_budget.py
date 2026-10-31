"""App usage counters are informative, not spending limits."""
import uuid
from app.workspace_store import init_db
from app.budget import reserve, budget_status


def test_usage_counter_is_uncapped(monkeypatch):
    init_db()
    provider = "test-" + uuid.uuid4().hex
    monkeypatch.setenv("OTHER_APP_BUDGET_CENTS", "2")
    for _ in range(3):
        reserve(provider, 1)
    status = budget_status(provider)
    assert status["reserved_usd"] == 0.03
    assert status["cap_usd"] is None
    assert status["remaining_usd"] is None


def test_zero_legacy_budget_does_not_restrict_usage(monkeypatch):
    init_db()
    monkeypatch.setenv("META_APP_BUDGET_CENTS", "0")
    provider = "test-" + uuid.uuid4().hex
    reserve(provider, 5)
    assert budget_status(provider)["reserved_usd"] == 0.05
