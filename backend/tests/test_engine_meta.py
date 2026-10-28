import json
import pytest
from app.meta_client import MetaClient,MetaError
from app import meta_client
from tests.test_meta_client import live,transport
from tests.test_engine_inputs import audio,grounded


def test_grounded_search_http_contract_and_tool_bound(live,monkeypatch):
    calls=transport(monkeypatch,grounded())
    result=MetaClient(**live,max_tokens=1800).search("Find workshops and cite public sources")
    assert result["provenance"]=="live_meta" and result["data"]["searched"] is True
    body=json.loads(calls[0].content)
    assert str(calls[0].url)=="https://api.meta.ai/v1/responses"
    assert body["max_tool_calls"]==1 and body["store"] is False
    assert body["tools"]==[{"type":"web_search","search_context_size":"low"}]
    assert body["include"]==["web_search_call.results"] and len(calls)==1


def test_transcription_exact_multipart_contract(live,monkeypatch):
    calls=transport(monkeypatch,{"sessionId":"fixture","transcript":"Improve qualified inquiries.","audioDurationMs":1000,"turns":[]})
    result=MetaClient(**live).transcribe(audio(),"audio/wav")
    assert result["provenance"]=="live_meta" and result["data"]["transcript"]=="Improve qualified inquiries."
    request=calls[0]
    assert str(request.url)=="https://api.meta.ai/v1/asr/transcribe"
    assert b'name="request"' in request.content and b'name="audio"' in request.content
    assert b'"audioEncoding": "WAV"' in request.content and b'"mode": "PUSH_TO_TALK"' in request.content
    assert request.headers["accept"]=="application/json" and len(calls)==1


@pytest.mark.parametrize("disabled",["ALLOW_PAID_INFERENCE","ENABLE_LIVE_MULTIMODAL","SENTINELX_MODE","INFERENCE_PROVIDER"])
def test_voice_and_search_off_gates_do_not_construct_transport(live,monkeypatch,disabled):
    monkeypatch.setenv(disabled,"demo" if disabled=="INFERENCE_PROVIDER" else "false")
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:pytest.fail("Disabled capability called SDK"))
    assert MetaClient(**live).search("Public workshop evidence")["provenance"]=="sample"
    assert MetaClient(**live).transcribe(audio(),"audio/wav")["provenance"]=="sample"


def test_no_search_or_empty_transcript_is_not_treated_as_success(live,monkeypatch):
    payload=grounded();payload["output"]=payload["output"][1:]
    calls=transport(monkeypatch,payload)
    with pytest.raises(MetaError):MetaClient(**live).search("Find public evidence")
    assert len(calls)==1
