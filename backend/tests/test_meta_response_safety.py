"""Offline fixtures confirm no hidden Meta costs, retries, or secret leakage."""
import io
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from PIL import Image

from app import providers
from scripts import meta_smoke

class FakeMetaClient:
    def __init__(self):
        self.calls=[]
    @staticmethod
    def _enabled(multimodal):
        return True
    def text(self,system,user,json_schema=None):
        self.calls.append("text")
        return {"provenance":"live_meta","model":"muse-spark-1.3",
                "data":{"answer":"OK"} if json_schema else {"text":"OK"},
                "usage":{"prompt_tokens":6,"completion_tokens":8,"reasoning_tokens":2},
                "finish_reason":"stop"}
    def vision(self,payload,mime,prompt,json_schema=None):
        self.calls.append("vision")
        return {"provenance":"live_meta","model":"muse-spark-1.3","data":{"color":"red"}}
    def image(self,prompt,size="1024x1024"):
        import base64
        output=io.BytesIO();Image.new("RGB",(40,40),"red").save(output,format="PNG")
        self.calls.append("image")
        return {"provenance":"live_meta","model":"muse-image-1.0",
                "data":{"image_b64":base64.b64encode(output.getvalue()).decode()}}

def setup_smoke(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY","fake-secret-never-print")
    monkeypatch.setenv("META_SMOKE_ACK","I_ACKNOWLEDGE_ONE_PAID_REQUEST")
    monkeypatch.setattr(meta_smoke,"init_db",lambda:None)
    monkeypatch.setattr(meta_smoke,"MetaClient",FakeMetaClient)

@pytest.mark.parametrize("capability",["text","vision","image"])
def test_smoke_one_capability_sanitized(monkeypatch,capsys,capability):
    setup_smoke(monkeypatch)
    monkeypatch.setenv("META_SMOKE_CAPABILITY",capability)
    assert meta_smoke.main()==0
    output=capsys.readouterr().out
    assert "fake-secret-never-print" not in output
    assert "Live Meta provenance confirmed: True" in output
    assert "Usable validated response: True" in output

def test_smoke_requires_authorization(monkeypatch):
    setup_smoke(monkeypatch)
    monkeypatch.delenv("META_SMOKE_ACK")
    assert meta_smoke.main()==2

def test_meta_provider_uses_shared_client(monkeypatch):
    monkeypatch.setattr(providers,"configured_provider",lambda:providers.ProviderConfig(
        "meta","https://api.meta.ai/v1","muse-spark-1.3","fake"))
    from app import meta_client
    fake=FakeMetaClient()
    monkeypatch.setattr(meta_client,"MetaClient",lambda:fake)
    result=providers.infer("Assess this business")
    assert result["status"]=="completed"
    assert result["text"]=="OK"
    assert result["usage"]["reasoning_tokens"]==2
    assert fake.calls==["text"]

def test_meta_provider_fails_closed_on_demo_provenance(monkeypatch):
    monkeypatch.setattr(providers,"configured_provider",lambda:providers.ProviderConfig(
        "meta","https://api.meta.ai/v1","muse-spark-1.3","fake"))
    from app import meta_client
    monkeypatch.setattr(meta_client,"MetaClient",lambda:SimpleNamespace(
        text=lambda *args:{"provenance":"sample","data":{"text":"sample"}}))
    with pytest.raises(ValueError,match="not enabled"):providers.infer("Check")
