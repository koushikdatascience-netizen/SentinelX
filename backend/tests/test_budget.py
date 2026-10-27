import os
import pytest
from app.workspace_store import init_db
from app.budget import reserve, budget_status

def test_budget_reservation_fails_closed(monkeypatch):
    init_db()
    import uuid
    provider="test-"+uuid.uuid4().hex
    monkeypatch.setenv("OTHER_APP_BUDGET_CENTS","2")
    reserve(provider,1)
    reserve(provider,1)
    with pytest.raises(ValueError,match="budget"):
        reserve(provider,1)
    status=budget_status(provider)
    assert status["remaining_usd"]==0

def test_zero_budget_prevents_spending(monkeypatch):
    init_db()
    monkeypatch.setenv("META_APP_BUDGET_CENTS","0")
    with pytest.raises(ValueError,match="budget"):
        reserve("meta",5)
