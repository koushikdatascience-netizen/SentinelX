"""Facade and manual smoke authorization tests; never call a real provider."""
from unittest.mock import Mock
import pytest
from app import providers, meta_client
from scripts import meta_smoke


def test_smoke_requires_explicit_ack_before_client_creation(monkeypatch):
    monkeypatch.delenv("META_SMOKE_ACK",raising=False)
    factory=Mock();monkeypatch.setattr(meta_smoke,"MetaClient",factory)
    assert meta_smoke.main()==2
    factory.assert_not_called()


@pytest.mark.parametrize("capability",["text","vision","image"])
def test_smoke_one_selected_capability_and_sanitized_output(monkeypatch,capsys,capability):
    for key,value in {"META_SMOKE_ACK":"I_ACKNOWLEDGE_ONE_PAID_REQUEST","META_SMOKE_CAPABILITY":capability,
                      "MODEL_API_KEY":"test-secret-not-for-logs","INFERENCE_PROVIDER":"meta","ALLOW_PAID_INFERENCE":"true",
                      "ENABLE_LIVE_MULTIMODAL":"true","SENTINELX_MODE":"live",
                      "DATABASE_URL":"sqlite:///./meta-smoke.sqlite3"}.items():
        monkeypatch.setenv(key,value)
    client=Mock()
    for name in ("text","vision","image"):
        getattr(client,name).return_value={"provenance":"live_meta","model":"test-model","data":"private-output"}
    monkeypatch.setattr(meta_smoke,"MetaClient",Mock(return_value=client))
    assert meta_smoke.main()==0
    assert sum(getattr(client,name).call_count for name in ("text","vision","image"))==1
    assert getattr(client,capability).call_count==1
    output=capsys.readouterr()
    assert "private-output" not in output.out+output.err
    assert "test-secret-not-for-logs" not in output.out+output.err


def test_smoke_does_not_fall_back_silently(monkeypatch):
    monkeypatch.setenv("META_SMOKE_ACK","I_ACKNOWLEDGE_ONE_PAID_REQUEST")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    factory=Mock();monkeypatch.setattr(meta_smoke,"MetaClient",factory)
    assert meta_smoke.main()==2
    factory.assert_not_called()


def test_provider_delegates_to_single_client(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    client=Mock();client.text.return_value={"provenance":"sample","model":"muse-spark-1.3","data":"Fixture"}
    factory=Mock(return_value=client);monkeypatch.setattr(meta_client,"MetaClient",factory)
    result=providers.infer("Test input",owner_id="owner",workspace_id="workspace",run_id="run")
    assert result["status"]=="simulated" and result["provenance"]=="sample"
    factory.assert_called_once_with(owner_id="owner",workspace_id="workspace",run_id="run")
    client.text.assert_called_once()


def test_smoke_rejects_production_database(monkeypatch):
    for key,value in {"META_SMOKE_ACK":"I_ACKNOWLEDGE_ONE_PAID_REQUEST","META_SMOKE_CAPABILITY":"text",
                      "MODEL_API_KEY":"test-only","INFERENCE_PROVIDER":"meta","ALLOW_PAID_INFERENCE":"true",
                      "ENABLE_LIVE_MULTIMODAL":"true","SENTINELX_MODE":"live",
                      "DATABASE_URL":"postgresql://never-access-this"}.items():
        monkeypatch.setenv(key,value)
    factory=Mock();monkeypatch.setattr(meta_smoke,"MetaClient",factory)
    assert meta_smoke.main()==2
    factory.assert_not_called()
