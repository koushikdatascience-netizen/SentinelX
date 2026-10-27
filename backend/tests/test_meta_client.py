import json
from types import SimpleNamespace
import pytest
from app.meta_client import MetaClient, MetaResponseError, NotSupported

def completion(content='{"ok":true}', finish="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=content))])

class SDK:
    def __init__(self):
        self.calls=[]
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.complete))
        self.images=SimpleNamespace(generate=self.generate)
    def complete(self,**kwargs):
        self.calls.append(kwargs)
        return completion()
    def generate(self,**kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json="YQ==")])

def client(monkeypatch):
    sdk=SDK()
    monkeypatch.setenv("MODEL_API_KEY","not-a-real-key")
    monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    monkeypatch.setenv("SENTINELX_MODE","live")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true")
    return MetaClient(sdk_factory=lambda **kwargs: sdk),sdk

def test_demo_no_key_no_reservation(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","false")
    assert MetaClient().text("system","prompt")["provenance"]=="sample"
    assert MetaClient().image("Generate a product photo")["provenance"]=="sample"
    assert MetaClient().vision(b"png","image/png","Score")["provenance"]=="sample"
    assert MetaClient().segment(b"png","image/png")["provenance"]=="sample"

def test_text_structured_budget_first(monkeypatch):
    c,sdk=client(monkeypatch);events=[]
    monkeypatch.setattr("app.meta_client.reserve",lambda p,cents:events.append((p,cents)))
    out=c.text("Safe system","Evidence",{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"],"additionalProperties":False})
    assert events==[("meta",5)]
    assert out["provenance"]=="live_meta" and out["data"]=={"ok":True}
    assert sdk.calls[0]["response_format"]["type"]=="json_schema"
    assert sdk.calls[0]["max_completion_tokens"]==1200

def test_vision_content_parts(monkeypatch):
    c,sdk=client(monkeypatch)
    monkeypatch.setattr("app.meta_client.reserve",lambda *args:None)
    assert c.vision(b"imagebytes","image/png","Review")["provenance"]=="live_meta"
    assert sdk.calls[0]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert c.image("Generate a furniture photo")["data"]["image_b64"]=="YQ=="

def test_malformed_and_truncated_responses_fail_closed(monkeypatch):
    c,sdk=client(monkeypatch)
    monkeypatch.setattr("app.meta_client.reserve",lambda *args:None)
    sdk.chat.completions.create=lambda **kwargs:completion("not-json")
    with pytest.raises(MetaResponseError):c.text("system","user",{"type":"object"})
    sdk.chat.completions.create=lambda **kwargs:completion("unfinished","length")
    with pytest.raises(MetaResponseError):c.text("system","user")

def test_sam_fails_without_spend(monkeypatch):
    c,sdk=client(monkeypatch)
    monkeypatch.setattr("app.meta_client.reserve",lambda *args:pytest.fail("unexpected budget reservation"))
    with pytest.raises(NotSupported):c.segment(b"image","image/png")

def test_multimodal_disabled(monkeypatch):
    c,sdk=client(monkeypatch)
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","false")
    assert c.image("A photo of handmade furniture")["provenance"]=="sample"
    assert sdk.calls==[]
