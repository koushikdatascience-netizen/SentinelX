from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app import meta_client
from tests.test_meta_client import png
from tests.test_engine_inputs import audio
from tests.test_mission_routes import live_transport,inputs
from tests.test_meta_client import live,transport,chat


def test_context_handoff_keeps_real_visual_observations_and_original_audit_text():
    from app.engine_context import context_handoff
    original="**Grounded Visual Business Twin**\n\n> "+"Unverified interpretation. "*30+"\n\nObserved turned wooden legs on a plain background.\nUnknown: exact dimensions."
    twin={"id":"twin","kind":"business_twin","provenance":"live_meta","sha256":"digest","text":original}
    notes={"id":"notes","kind":"business_twin","provenance":"user_supplied","text":"> Keep this owner instruction."}
    selected=context_handoff([twin,notes])
    assert "Observed turned wooden legs" in selected[0]["text"] and "Unverified interpretation." not in selected[0]["text"]
    assert "Unknown: exact dimensions." in selected[0]["text"]
    assert selected[1]["text"]==notes["text"] and twin["text"]==original


def test_notes_and_sample_twin_are_owned_reusable_and_free(authenticated_client,monkeypatch):
    client=authenticated_client;wid=inputs(client)["workspace_id"]
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:pytest.fail("Sample context called SDK"))
    data={"workspace_id":wid,"notes":"We only make trade components in bulk; customers provide design references.","consent":"true"}
    notes=client.post("/api/v1/business-context",data=data)
    assert notes.status_code==201,notes.text
    assert notes.json()["provenance"]=="user_supplied"
    assert client.post("/api/v1/business-context",data=data).json()["id"]==notes.json()["id"]
    twin=client.post("/api/v1/business-context",data={**data,"generation_mode":"sample"},files={"file":("product.png",png(),"image/png")})
    assert twin.status_code==201,twin.text
    assert twin.json()["provenance"]=="sample" and twin.json()["sha256"]
    assert "Original media bytes are not saved" in twin.json()["limitation"]
    voice=client.post("/api/v1/business-context",data={**data,"kind":"voice"},files={"file":("goal.wav",audio(),"audio/wav")})
    assert voice.status_code==201 and voice.json()["provenance"]=="sample"
    assert len(client.get("/api/v1/business-context",params={"workspace_id":wid}).json())==3
    assert TestClient(app).get("/api/v1/business-context",params={"workspace_id":wid}).status_code==401
    other=TestClient(app);account={"email":f"context-{uuid4()}@example.org","password":"StrongPassword123"}
    other.post("/api/v1/auth/register",json=account);token=other.post("/api/v1/auth/login",json=account).json()["access_token"]
    other.headers["Authorization"]="Bearer "+token
    assert other.get("/api/v1/business-context",params={"workspace_id":wid}).status_code==404
    assert other.post("/api/v1/business-context",data=data).status_code==404


def test_context_consent_validation_and_sample_live_isolation(authenticated_client,monkeypatch):
    client=authenticated_client;body=inputs(client);wid=body["workspace_id"]
    assert client.post("/api/v1/business-context",data={"workspace_id":wid,"notes":"A business brief"}).status_code==422
    assert client.post("/api/v1/business-context",data={"workspace_id":wid,"kind":"voice","consent":"true"},files={"file":("bad.wav",b"bad","audio/wav")}).status_code==422
    twin=client.post("/api/v1/business-context",data={"workspace_id":wid,"consent":"true"},files={"file":("p.png",png(),"image/png")}).json()
    calls=live_transport(monkeypatch)
    response=client.post("/api/v1/missions",json={**body,"generation_mode":"live","consent_public_fetch":True,"context_ids":[twin["id"]]})
    assert response.status_code==422 and calls==[]
    assert client.post("/api/v1/missions",json={**body,"context_ids":[str(uuid4())]}).status_code==404


def test_live_context_and_voice_use_owned_guarded_transport_and_reuse_results(authenticated_client,live,monkeypatch):
    monkeypatch.setenv("CAMPAIGN_WORKSPACE_MAX_ATTEMPTS","20")
    client=authenticated_client;wid=inputs(client)["workspace_id"]
    calls=transport(monkeypatch,chat("Visible product on a plain background; exact dimensions and production capacity are unknown."))
    data={"workspace_id":wid,"consent":"true","generation_mode":"live","notes":"Trade components; retain the existing quotation process."}
    first=client.post("/api/v1/business-context",data=data,files={"file":("product.png",png(),"image/png")})
    assert first.status_code==201,first.text
    assert first.json()["provenance"]=="live_meta" and len(calls)==1
    again=client.post("/api/v1/business-context",data=data,files={"file":("product.png",png(),"image/png")})
    assert again.json()["id"]==first.json()["id"] and len(calls)==1
    voice_calls=transport(monkeypatch,{"sessionId":"fixture","transcript":"Research qualified trade inquiries.","audioDurationMs":1000,"turns":[]})
    voice=client.post("/api/v1/business-context",data={**data,"kind":"voice"},files={"file":("goal.wav",audio(),"audio/wav")})
    assert voice.status_code==201,voice.text
    assert voice.json()["text"]=="Research qualified trade inquiries." and len(voice_calls)==1
    assert "audio_bytes" not in voice.json() and "image_bytes" not in first.json()
