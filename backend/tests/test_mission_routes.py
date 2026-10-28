import json
from datetime import datetime,timezone
from uuid import uuid4
from urllib.parse import parse_qs,urlsplit
import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from sqlalchemy import select
from app.main import app
from app import mission_routes,meta_client
from app.mission import sample_source,sample_plan
from app.workspace_store import SessionLocal,LandingLead


def inputs(client):
    wid=client.post("/api/v1/workspaces",json={"name":"Mission workshop"}).json()["id"]
    return {"workspace_id":wid,"request_id":str(uuid4()),"website":"https://example.com/",
            "goal":"Improve the furniture consultation inquiry journey","generation_mode":"sample"}


def test_sample_mission_is_persistent_isolated_and_zero_network(authenticated_client,monkeypatch):
    client=authenticated_client;body=inputs(client)
    monkeypatch.setattr(mission_routes,"collect_page",lambda url:pytest.fail("Sample mode performed network access"))
    result=client.post("/api/v1/missions",json=body)
    assert result.status_code==201,result.text
    data=result.json();assert data["provenance"]=="sample" and data["status"]=="completed"
    assert len(data["trace"])==4 and all(step["status"]=="completed" for step in data["trace"])
    assert data["sources"][0]["origin"]=="fixture"
    path=f'/api/v1/missions/{data["id"]}'
    assert client.get(path,params={"workspace_id":body["workspace_id"]}).json()==data
    assert client.get(path,params={"workspace_id":"not-mine"}).status_code==404
    assert TestClient(app).get(path,params={"workspace_id":body["workspace_id"]}).status_code==401
    assert client.get(path+"/report",params={"workspace_id":body["workspace_id"]}).json()==data
    assert client.get("/api/v1/missions",params={"workspace_id":body["workspace_id"]}).json()[0]["id"]==data["id"]


def live_transport(monkeypatch,plan=None):
    for key,value in {"INFERENCE_PROVIDER":"meta","SENTINELX_MODE":"live","ALLOW_PAID_INFERENCE":"true",
       "ENABLE_LIVE_MULTIMODAL":"true","MODEL_API_KEY":"offline-mission-test-only","META_MODEL":"muse-spark-1.3",
       "CAMPAIGN_WORKSPACE_MAX_ATTEMPTS":"20","META_APP_BUDGET_CENTS":"1000000",
       "META_WORKSPACE_BUDGET_CENTS":"100","META_RUN_BUDGET_CENTS":"50"}.items():monkeypatch.setenv(key,value)
    source={**sample_source(),"origin":"retrieved_public_page","collected_at":datetime.now(timezone.utc).isoformat(),"sha256":"0"*64}
    monkeypatch.setattr(mission_routes,"collect_page",lambda url:{**source,"url":url})
    calls=[]
    def send(request):
        calls.append(request)
        return httpx.Response(200,json={"id":"fixture","object":"chat.completion","created":1,"model":"muse-spark-1.3",
           "choices":[{"index":0,"message":{"role":"assistant","content":json.dumps(plan or sample_plan())},"finish_reason":"stop"}],
           "usage":{"prompt_tokens":20,"completion_tokens":50,"total_tokens":70}})
    def factory(**kwargs):
        assert kwargs["max_retries"]==0
        return OpenAI(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(send)))
    monkeypatch.setattr(meta_client,"OpenAI",factory)
    return calls


def test_live_mission_one_budgeted_http_call_and_idempotent_replay(authenticated_client,monkeypatch):
    calls=live_transport(monkeypatch);client=authenticated_client;body=inputs(client)
    body.update(generation_mode="live",consent_public_fetch=True)
    result=client.post("/api/v1/missions",json=body)
    assert result.status_code==201,result.text
    assert result.json()["provenance"]=="live_meta" and len(calls)==1
    assert result.json()["trace"][2]["kind"]=="model"
    assert client.post("/api/v1/missions",json=body).json()==result.json()
    assert len(calls)==1
    assert client.post("/api/v1/missions",json={**body,"goal":"A different business goal for the same ID"}).status_code==409
    request=json.loads(calls[0].content)
    assert request["max_completion_tokens"]==2400
    assert "UNTRUSTED DATA" in request["messages"][0]["content"]
    budget=client.get("/api/v1/inference/budget").json()
    assert budget["meta"]["reserved_usd"]>=0.05


def test_live_requires_consent_before_retrieval(authenticated_client,monkeypatch):
    calls=live_transport(monkeypatch);body=inputs(authenticated_client);body["generation_mode"]="live"
    monkeypatch.setattr(mission_routes,"collect_page",lambda url:pytest.fail("No consent"))
    assert authenticated_client.post("/api/v1/missions",json=body).status_code==422
    assert calls==[]


def test_invented_quote_stops_mission_and_preserves_failed_trace(authenticated_client,monkeypatch):
    plan=sample_plan();plan["opportunities"][0]["quote"]="This statement was never in the source."
    calls=live_transport(monkeypatch,plan);body=inputs(authenticated_client)
    body.update(generation_mode="live",consent_public_fetch=True)
    assert authenticated_client.post("/api/v1/missions",json=body).status_code==502
    saved=authenticated_client.get(f'/api/v1/missions/{body["request_id"]}',params={"workspace_id":body["workspace_id"]}).json()
    assert saved["status"]=="failed" and saved["plan"] is None
    assert saved["trace"][-1]["agent"]=="Evidence verifier" and saved["trace"][-1]["status"]=="failed"
    assert authenticated_client.post("/api/v1/missions",json=body).status_code==409
    assert len(calls)==1


def test_sample_guest_cannot_fetch_live_web(authenticated_client,monkeypatch):
    from app.workspace_store import User,Workspace
    calls=live_transport(monkeypatch);body=inputs(authenticated_client)
    with SessionLocal.begin() as db:
        workspace=db.get(Workspace,body["workspace_id"]);db.get(User,workspace.owner_id).is_demo=True
    body.update(generation_mode="live",consent_public_fetch=True)
    # Demo users without a valid demo-session record are rejected by authentication.
    assert authenticated_client.post("/api/v1/missions",json=body).status_code in (401,403)
    assert calls==[]


def test_approved_public_execution_verification_and_cleanup(authenticated_client,monkeypatch):
    client=authenticated_client;body=inputs(client);scope={"workspace_id":body["workspace_id"]}
    mission=client.post("/api/v1/missions",json=body).json()
    campaign=client.post("/api/v1/campaigns",json={**scope,"mission_id":mission["id"],"generation_mode":"sample",
       "business_description":"We make furniture to order and discuss each client's requirements.","goal":body["goal"]}).json()
    assert campaign["audit"]["mission_id"]==mission["id"]
    assert campaign["audit"]["evidence"][-1]["type"]=="fixture"
    page=client.post("/api/v1/landing/generate",json={**scope,"campaign_id":campaign["id"],"business_name":"Sample Workshop","generation_mode":"sample"}).json()
    path=f'/api/v1/missions/{mission["id"]}/verify'
    verify={"page_id":page["id"],"consent_synthetic_inquiry":True}
    assert client.post(path,params=scope,json=verify).status_code==409
    board=client.get(f'/api/v1/campaigns/{campaign["id"]}/board',params=scope).json()
    review=next(item for item in board if item["target_kind"]=="landing")
    client.post(f'/api/v1/approvals/{review["id"]}/decide',params=scope,json={"decision":"approved","note":"Sample verification test"})
    client.patch(f'/api/v1/landing/{page["id"]}',params=scope,json={"published":True})
    assert client.post(path,params=scope,json={"page_id":page["id"]}).status_code==422
    monkeypatch.setenv("CORS_ORIGINS","https://sentinelx.example.com")
    requests=[]
    def public(url,method="GET",body=None):
        requests.append((url,method))
        assert url.startswith("https://sentinelx.example.com/p/")
        response=client.get(urlsplit(url).path) if method=="GET" else client.post(urlsplit(url).path,
                 data={key:values[0] for key,values in parse_qs(body.decode()).items()})
        return {"status":response.status_code,"html":response.text}
    monkeypatch.setattr(mission_routes,"request_public",public)
    result=client.post(path,params=scope,json=verify)
    assert result.status_code==200,result.text
    assert result.json()["passed"] is True and result.json()["business_impact_measured"] is False
    assert len(requests)==2
    assert client.get(f'/api/v1/landing/{page["id"]}/leads',params=scope).json()==[]
    # Even if a proxy disconnects after storage, finally must remove the synthetic lead.
    def disconnect(url,method="GET",body=None):
        result=public(url,method,body)
        if method=="POST":raise OSError("test disconnect after storage")
        return result
    monkeypatch.setattr(mission_routes,"request_public",disconnect)
    assert client.post(path,params=scope,json=verify).json()["passed"] is False
    assert client.get(f'/api/v1/landing/{page["id"]}/leads',params=scope).json()==[]
    assert client.post(path,params={"workspace_id":"not-mine"},json=verify).status_code==404
