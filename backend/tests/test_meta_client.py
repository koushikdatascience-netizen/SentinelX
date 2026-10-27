"""Meta HTTP contract tests: no real network or credentials."""
import base64
import io
import json
from uuid import uuid4
from unittest.mock import Mock
import httpx
import pytest
from openai import OpenAI as SDK
from PIL import Image
from app import meta_client
from app.meta_client import MetaClient, MetaError, NotSupported
from app.workspace_store import init_db, SessionLocal, User, Workspace, WorkflowRun
from app.budget import reserve_meta, ApiBudget
from sqlalchemy import select


@pytest.fixture
def live(monkeypatch):
    for name,value in {"INFERENCE_PROVIDER":"meta","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true",
                       "MODEL_API_KEY":"test-only-not-a-real-key","META_MODEL":"muse-spark-1.3",
                       "META_APP_BUDGET_CENTS":"1000000","META_WORKSPACE_BUDGET_CENTS":"10","META_RUN_BUDGET_CENTS":"10"}.items():
        monkeypatch.setenv(name,value)
    init_db()
    with SessionLocal.begin() as db:
        user=User(email=f"client-{uuid4()}@example.invalid",password_hash="test-only")
        db.add(user);db.flush()
        workspace=Workspace(owner_id=user.id,name="Client test")
        db.add(workspace);db.flush()
        run=WorkflowRun(workspace_id=workspace.id,website="https://example.invalid",objective="Contract test")
        db.add(run);db.flush()
        scope={"owner_id":user.id,"workspace_id":workspace.id,"run_id":run.id}
    return scope


def png():
    image=io.BytesIO();Image.new("RGB",(8,8),(255,0,0)).save(image,format="PNG")
    return image.getvalue()


def transport(monkeypatch, payload=None, status=200, failure=None):
    calls=[]
    def handle(request):
        calls.append(request)
        if failure: raise failure
        return httpx.Response(status,json=payload)
    def factory(**kwargs):
        assert kwargs["max_retries"]==0
        assert kwargs["timeout"]==30
        return SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(meta_client,"OpenAI",factory)
    return calls


def chat(text="OK", reason="stop", choices=True):
    return {"id":"test", "object":"chat.completion","created":1,"model":"muse-spark-1.3",
            "choices":[{"index":0,"message":{"role":"assistant","content":text},"finish_reason":reason}] if choices else [],
            "usage":{"prompt_tokens":10,"completion_tokens":40,"total_tokens":50,
                     "completion_tokens_details":{"reasoning_tokens":38}}}


@pytest.mark.parametrize("capability",["text","vision","image","segment"])
@pytest.mark.parametrize("disabled",["ALLOW_PAID_INFERENCE","ENABLE_LIVE_MULTIMODAL","INFERENCE_PROVIDER"])
def test_off_flags_never_construct_transport(live,monkeypatch,capability,disabled):
    monkeypatch.setenv(disabled,"demo" if disabled=="INFERENCE_PROVIDER" else "false")
    factory=Mock();monkeypatch.setattr(meta_client,"OpenAI",factory)
    client=MetaClient(**live)
    operations={"text":lambda:client.text("System","User"),"vision":lambda:client.vision(png(),"image/png","Describe"),
                "image":lambda:client.image("A blue circle","1024x1024"),"segment":lambda:client.segment(png(),"image/png")}
    first=operations[capability]();assert first==operations[capability]()
    assert first["provenance"]=="sample"
    factory.assert_not_called()


def test_text_and_json_schema_http_contract(live,monkeypatch):
    schema={"type":"object","properties":{"answer":{"type":"string"}},"required":["answer"],"additionalProperties":False}
    calls=transport(monkeypatch,chat('{"answer":"OK"}'))
    result=MetaClient(**live).text("System rules","User prompt",schema)
    assert result["data"]=={"answer":"OK"} and result["provenance"]=="live_meta"
    assert result["usage"]["reasoning_tokens"]==38
    body=json.loads(calls[0].content)
    assert str(calls[0].url)=="https://api.meta.ai/v1/chat/completions"
    assert calls[0].headers["authorization"]=="Bearer test-only-not-a-real-key"
    assert body["response_format"]["json_schema"]["schema"]==schema
    assert body["reasoning_effort"]=="minimal" and body["max_completion_tokens"]==500
    assert body["messages"][0]["role"]=="developer"


def test_vision_data_url_contract(live,monkeypatch):
    calls=transport(monkeypatch,chat("A red square"))
    result=MetaClient(**live).vision(png(),"image/png","Describe")
    body=json.loads(calls[0].content)
    url=body["messages"][0]["content"][1]["image_url"]["url"]
    assert base64.b64decode(url.split(",")[1])==png()
    assert result["provenance"]=="live_meta"


def test_image_contract(live,monkeypatch):
    encoded=base64.b64encode(png()).decode()
    calls=transport(monkeypatch,{"created":1,"data":[{"b64_json":encoded}]})
    result=MetaClient(**live).image("A blue circle","1024x1536")
    assert result["data"]["b64_json"]==encoded
    assert str(calls[0].url)=="https://api.meta.ai/v1/images/generations"
    body=json.loads(calls[0].content)
    assert body=={"model":"muse-image-1.0","prompt":"A blue circle","size":"1024x1536","n":1,"response_format":"b64_json"}


@pytest.mark.parametrize("payload",[chat(""),chat("partial","length"),chat(choices=False),chat(None)])
def test_empty_incomplete_and_missing_choices_fail_no_retry(live,monkeypatch,payload):
    calls=transport(monkeypatch,payload)
    with pytest.raises(MetaError,match="No retry made"):
        MetaClient(**live).text("System","User")
    assert len(calls)==1


@pytest.mark.parametrize("status",[400,401,429,500])
def test_http_errors_sanitized_and_never_retried(live,monkeypatch,status,capsys):
    calls=transport(monkeypatch,{"error":{"message":"private-provider-payload"}},status)
    with pytest.raises(MetaError) as error:
        MetaClient(**live).text("System","User")
    assert "private-provider-payload" not in str(error.value)
    assert len(calls)==1
    assert capsys.readouterr().out==""


def test_timeout_not_retried(live,monkeypatch):
    calls=transport(monkeypatch,failure=httpx.ReadTimeout("private payload"))
    with pytest.raises(MetaError):MetaClient(**live).text("System","User")
    assert len(calls)==1


def test_schema_output_is_locally_validated(live,monkeypatch):
    transport(monkeypatch,chat('{"wrong":1}'))
    with pytest.raises(MetaError,match="schema"):
        MetaClient(**live).text("System","User",{"type":"object","required":["answer"]})


def test_invalid_input_rejected_before_charge_or_transport(live,monkeypatch):
    reserve=Mock();factory=Mock()
    monkeypatch.setattr(meta_client,"reserve_meta",reserve);monkeypatch.setattr(meta_client,"OpenAI",factory)
    client=MetaClient(**live)
    for operation in (lambda:client.text("System","x"*6001),lambda:client.vision(b"bad","image/png","Describe"),
                      lambda:client.vision(png(),"image/jpeg","Describe"),lambda:client.image("Blue","bad"),
                      lambda:client.text("System","User",{"$ref":"http://localhost/private"})):
        with pytest.raises(ValueError):operation()
    reserve.assert_not_called();factory.assert_not_called()


def test_unsupported_adapters_never_charge(live,monkeypatch):
    reserve=Mock();monkeypatch.setattr(meta_client,"reserve_meta",reserve)
    with pytest.raises(NotSupported):MetaClient(**live).segment(png(),"image/png")
    with pytest.raises(NotSupported):MetaClient(**live).transcribe(b"audio","audio/wav")
    reserve.assert_not_called()


@pytest.mark.parametrize("limit",["META_APP_BUDGET_CENTS","META_WORKSPACE_BUDGET_CENTS","META_RUN_BUDGET_CENTS"])
def test_budget_rolls_back_all_scopes(live,monkeypatch,limit):
    monkeypatch.setenv(limit,"0")
    with SessionLocal() as db: before={row.provider:row.reserved_cents for row in db.scalars(select(ApiBudget))}
    calls=transport(monkeypatch,chat())
    with pytest.raises(ValueError):MetaClient(**live).text("System","User")
    with SessionLocal() as db: after={row.provider:row.reserved_cents for row in db.scalars(select(ApiBudget))}
    assert before==after and calls==[]


def test_run_cap_and_workspace_cap_accumulate(live,monkeypatch):
    calls=transport(monkeypatch,chat())
    monkeypatch.setenv("META_RUN_BUDGET_CENTS","5")
    client=MetaClient(**live);client.text("System","User")
    with pytest.raises(ValueError):client.text("System","User")
    with SessionLocal.begin() as db:
        run=WorkflowRun(workspace_id=live["workspace_id"],website="https://example.invalid",objective="Second run")
        db.add(run);db.flush();run_id=run.id
    MetaClient(**{**live,"run_id":run_id}).text("System","User")
    with pytest.raises(ValueError):MetaClient(**{**live,"run_id":run_id}).text("System","User")
    assert len(calls)==2


def test_wrong_owner_or_missing_scope_never_calls(live,monkeypatch):
    calls=transport(monkeypatch,chat())
    for scope in ({},{**live,"owner_id":"another-owner"},{**live,"run_id":str(uuid4())}):
        with pytest.raises(ValueError):MetaClient(**scope).text("System","User")
    assert calls==[]


def test_concurrent_budget_is_atomic(live,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    monkeypatch.setenv("META_WORKSPACE_BUDGET_CENTS","5")
    barrier=Barrier(2)
    def attempt(_):
        barrier.wait(timeout=5)
        try:reserve_meta(**live,cents=5);return "reserved"
        except ValueError:return "blocked"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt,range(2)))==["blocked","reserved"]


def test_sample_structured_schema_and_valid_image(live,monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    schema={"type":"object","properties":{"label":{"type":"string"}},"required":["label"]}
    result=MetaClient().text("System","User",schema)
    assert result["provenance"]=="sample" and result["data"]=={"label":"Sample fixture"}
    data=MetaClient().image("A blue circle","1024x1024")["data"]
    with Image.open(io.BytesIO(base64.b64decode(data["b64_json"]))) as image:image.verify()


def test_failed_call_keeps_reservation(live,monkeypatch):
    monkeypatch.setenv("META_RUN_BUDGET_CENTS","5")
    calls=transport(monkeypatch,{"error":{"message":"private"}},500)
    with pytest.raises(MetaError):MetaClient(**live).text("System","User")
    with pytest.raises(ValueError):MetaClient(**live).text("System","User")
    assert len(calls)==1


def test_missing_key_or_unverified_model_no_charge(live,monkeypatch):
    reserve=Mock();monkeypatch.setattr(meta_client,"reserve_meta",reserve)
    monkeypatch.delenv("MODEL_API_KEY")
    with pytest.raises(MetaError):MetaClient(**live).text("System","User")
    monkeypatch.setenv("MODEL_API_KEY","test-only")
    monkeypatch.setenv("META_MODEL","unknown-model")
    with pytest.raises(NotSupported):MetaClient(**live).text("System","User")
    reserve.assert_not_called()


@pytest.mark.parametrize("payload",[{"created":1,"data":[]},{"created":1,"data":[{"b64_json":"not-base64"}]},
                                    {"created":1,"data":[{"b64_json":"bm90IGFuIGltYWdl"}]}])
def test_malformed_image_never_claims_success(live,monkeypatch,payload):
    calls=transport(monkeypatch,payload)
    with pytest.raises(MetaError):MetaClient(**live).image("A blue circle","1024x1024")
    assert len(calls)==1


def test_vision_schema_is_validated(live,monkeypatch):
    calls=transport(monkeypatch,chat('{"color":"red"}'))
    schema={"type":"object","properties":{"color":{"type":"string"}},"required":["color"]}
    result=MetaClient(**live).vision(png(),"image/png","Name color",schema)
    assert result["data"]=={"color":"red"}
    assert json.loads(calls[0].content)["response_format"]["json_schema"]["schema"]==schema
