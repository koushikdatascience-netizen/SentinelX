import json
from uuid import uuid4
import httpx
import pytest
from openai import OpenAI as SDK
from app import meta_client
from tests.test_business_onboarding import profile
from tests.test_business_visuals import enable
from tests.test_meta_client import chat
from tests.test_knowledge_routes import upload
from tests.test_business_data import CSV


def setup(client,monkeypatch,answer):
    wid=profile(client)["workspace_id"];enable(monkeypatch);calls=[]
    def handle(request):
        payload=json.loads(request.content);calls.append(payload)
        assert len(payload["messages"][0]["content"])<=2000
        return httpx.Response(200,json=chat(json.dumps(answer(payload))))
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    return wid,calls


def request(wid,**changes):return {"workspace_id":wid,"thread_id":str(uuid4()),"request_id":str(uuid4()),"message":"What should our workshop improve first?","focus":["strategy","marketing"],**changes}


def test_business_chat_retrieves_knowledge_is_idempotent_and_restores_owned_history(authenticated_client,monkeypatch):
    def answer(payload):
        context=json.loads(payload["messages"][1]["content"]);source=next(source for source in context["sources"] if source["id"].startswith("K"))
        return {"answer":"## Improve inquiry quality\nUse your supplied minimum-order policy in the quote journey.","citations":[{"source_id":source["id"],"quote":"Wholesale minimum is 30 units."}],"analysis":None}
    wid,calls=setup(authenticated_client,monkeypatch,answer)
    upload(authenticated_client,wid,"policy.txt",b"Wholesale minimum is 30 units.")
    body=request(wid,message="How should our minimum order policy guide inquiry messaging?")
    first=authenticated_client.post("/api/v1/business-chat",json=body);assert first.status_code==201,first.text
    assert first.json()["provenance"]=="live_meta" and first.json()["external_actions"]==0
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    assert authenticated_client.post("/api/v1/business-chat",json=body).json()["id"]==first.json()["id"] and len(calls)==1
    history=authenticated_client.get("/api/v1/business-chat",params={"workspace_id":wid,"thread_id":body["thread_id"]})
    assert history.status_code==200 and history.json()[0]["answer"]==first.json()["answer"]
    assert authenticated_client.get("/api/v1/business-chat/threads",params={"workspace_id":wid}).json()[0]["id"]==body["thread_id"]
    assert authenticated_client.get("/api/v1/business-chat",params={"workspace_id":"foreign","thread_id":body["thread_id"]}).status_code==404


def test_chat_data_question_uses_one_model_plan_and_real_local_calculations(authenticated_client,monkeypatch):
    wid,calls=setup(authenticated_client,monkeypatch,lambda payload:{"answer":"I will calculate total sales by region from the selected dataset. These values do not establish why sales changed.","citations":[],"analysis":{"aggregation":"sum","metric":"Sales","group_by":"Region","filters":[]}})
    asset=upload(authenticated_client,wid,"sales.csv",CSV)
    result=authenticated_client.post("/api/v1/business-chat",json=request(wid,dataset_id=asset["id"],message="Calculate total sales by region from this file."))
    assert result.status_code==201,result.text
    assert result.json()["analysis"]["results"]==[{"group":"North","value":"180.40"},{"group":"South","value":"40.20"}] and len(calls)==1


@pytest.mark.parametrize("failure",["citation","query"])
def test_invalid_chat_evidence_or_data_plan_stops_without_paid_replay(authenticated_client,monkeypatch,failure):
    answer={"answer":"This response must fail validation before being treated as valid.","citations":[{"source_id":"B1","quote":"Invented successful revenue growth"}],"analysis":None}
    if failure=="query":answer.update(citations=[],analysis={"aggregation":"execute_python","code":"private-dangerous-code"})
    wid,calls=setup(authenticated_client,monkeypatch,lambda payload:answer);body=request(wid)
    result=authenticated_client.post("/api/v1/business-chat",json=body)
    assert result.status_code==502 and "private-dangerous" not in result.text
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==409 and len(calls)==1


def test_chat_flags_consent_and_budget_block_transport(authenticated_client,monkeypatch):
    wid,calls=setup(authenticated_client,monkeypatch,lambda payload:pytest.fail("No transport expected"))
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    assert authenticated_client.post("/api/v1/business-chat",json=request(wid)).status_code==503
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true");monkeypatch.setenv("META_RUN_BUDGET_CENTS","0")
    assert authenticated_client.post("/api/v1/business-chat",json=request(wid)).status_code==429 and calls==[]


def test_chat_image_requires_consent_and_owned_intact_bytes(authenticated_client,monkeypatch):
    from app.business_store import BrandAsset
    from app.workspace_store import SessionLocal
    from tests.test_business_visuals import png
    wid=profile(authenticated_client)["workspace_id"];enable(monkeypatch);calls=[]
    response=authenticated_client.post(f"/api/v1/workspaces/{wid}/business-profile/assets",data={"kind":"logo","consent":"true"},files={"file":("logo.png",png("blue"),"image/png")})
    asset=response.json();assert response.status_code==201
    def handle(request):
        payload=json.loads(request.content);calls.append(payload)
        assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        return httpx.Response(200,json=chat(json.dumps({"answer":"The attached image has a blue background. This is a visual observation, not a measured business outcome.","citations":[],"analysis":None})))
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    body=request(wid,image_id=asset["id"])
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==422 and calls==[]
    body["image_consent"]=True
    assert authenticated_client.post("/api/v1/business-chat",json={**body,"image_id":str(uuid4())}).status_code==404
    result=authenticated_client.post("/api/v1/business-chat",json=body)
    assert result.status_code==201,result.text
    assert len(calls)==1 and result.json()["provenance"]=="live_meta"
    with SessionLocal() as db:db.get(BrandAsset,asset["id"]).sha256="0"*64;db.commit()
    assert authenticated_client.post("/api/v1/business-chat",json={**body,"request_id":str(uuid4())}).status_code==422 and len(calls)==1


def test_chat_knowledge_consent_and_prior_analysis_context(authenticated_client,monkeypatch):
    contexts=[]
    def answer(payload):
        context=json.loads(payload["messages"][1]["content"]);contexts.append(context)
        return {"answer":"I will calculate the selected dataset or explain the saved calculation without assuming its cause.","citations":[],"analysis":{"aggregation":"sum","metric":"Sales","group_by":"Region"} if len(contexts)==1 else None}
    wid,calls=setup(authenticated_client,monkeypatch,answer)
    asset=upload(authenticated_client,wid,"sales.csv",CSV);body=request(wid,dataset_id=asset["id"])
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==201
    followup={**body,"request_id":str(uuid4()),"message":"Explain the saved local sales result.","dataset_id":None}
    assert authenticated_client.post("/api/v1/business-chat",json=followup).status_code==201
    prior=next(source for source in contexts[1]["sources"] if source["id"]=="A1")
    assert "180.40" in prior["text"] and prior["origin"]=="local_calculation" and len(calls)==2
    from app.business_store import BusinessProfile
    from app.workspace_store import SessionLocal
    with SessionLocal() as db:db.get(BusinessProfile,wid).consent_at=None;db.commit()
    assert authenticated_client.post("/api/v1/business-chat",json={**followup,"request_id":str(uuid4())}).status_code==422 and len(calls)==2


def test_unselected_general_chat_does_not_run_tools(authenticated_client,monkeypatch):
    wid,calls=setup(authenticated_client,monkeypatch,lambda payload:{"answer":"4.","citations":[],"analysis":None})
    result=authenticated_client.post("/api/v1/business-chat",json=request(wid,message="What is two plus two?",focus=[],tools=[],use_knowledge=False))
    assert result.status_code==201,result.text
    assert len(calls)==1 and not result.json().get("tool_results")
    assert "general questions unrelated" in calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("selected",[["web_search","image"],["post","keywords","competitors"],["campaign","image"]])
def test_selected_chat_tools_execute_once_and_share_parent_budget(authenticated_client,monkeypatch,selected):
    import base64,hashlib
    from app.campaign import sample_plan
    from app.budget import ApiBudget
    from app.workspace_store import SessionLocal
    from tests.test_business_visuals import png
    from tests.test_engine_inputs import grounded
    wid=profile(authenticated_client)["workspace_id"];enable(monkeypatch);monkeypatch.setenv("CAMPAIGN_WORKSPACE_MAX_ATTEMPTS","3");calls=[]
    def handle(req):
        payload=json.loads(req.content);calls.append((req.url.path,payload))
        if req.url.path.endswith("/responses"):return httpx.Response(200,json=grounded())
        if req.url.path.endswith("/images/generations"):return httpx.Response(200,json={"created":1,"data":[{"b64_json":base64.b64encode(png("green")).decode()}]})
        schema=payload["response_format"]["json_schema"]["schema"]
        if "audit" in schema.get("properties",{}):
            audit,plan=sample_plan("Owner-supplied workshop","Qualified inquiries","en",["instagram","facebook"]);data={"audit":audit,"plan":plan}
        elif "caption" in schema.get("properties",{}):data={"title":"Workshop process","caption":"Ask us about custom workshop requirements.","hashtags":["#Woodwork"],"image_prompt":"An owner-approved workshop product in daylight.","video_scenes":["Show the product and invite a design inquiry."],"call_to_action":"Send your requirement.","assumptions":[]}
        else:data={"answer":"The selected tools finished. Review the saved drafts and public sources before using them.","citations":[],"analysis":None}
        return httpx.Response(200,json=chat(json.dumps(data)))
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    body=request(wid,tools=selected,tool_consent=True,message="Create useful workshop content and research for trade inquiries.")
    response=authenticated_client.post("/api/v1/business-chat",json=body)
    assert response.status_code==201,response.text
    assert {item["tool"] for item in response.json()["tool_results"]}==set(selected)
    assert all(item["status"]=="completed" for item in response.json()["tool_results"])
    assert len(calls)==len(selected)+1
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==201 and len(calls)==len(selected)+1
    with SessionLocal() as db:
        rows=db.query(ApiBudget).filter(ApiBudget.provider.like("mr:%")).all()
        key="mr:"+hashlib.sha256((wid+":"+body["request_id"]).encode()).hexdigest()[:32]
        assert db.get(ApiBudget,key).reserved_cents==sum(6 if path.endswith("/responses") else 5 for path,_ in calls)
    for item in response.json()["tool_results"]:
        if item["tool"]=="image":assert authenticated_client.get(f"/api/v1/workspaces/{wid}/business-profile/assets/{item['data']['asset_id']}").status_code==200
        if item["tool"]=="campaign":assert authenticated_client.get(f"/api/v1/campaigns/{item['data']['campaign_id']}",params={"workspace_id":wid}).status_code==200


def test_tool_consent_invalid_selections_and_partial_budget_stop(authenticated_client,monkeypatch):
    from tests.test_engine_inputs import grounded
    wid=profile(authenticated_client)["workspace_id"];enable(monkeypatch);calls=[]
    def handle(req):calls.append(req);return httpx.Response(200,json=grounded())
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    body=request(wid,tools=["web_search","image"])
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==422
    assert authenticated_client.post("/api/v1/business-chat",json={**body,"tools":["web_search","web_search"],"tool_consent":True}).status_code==422
    assert authenticated_client.post("/api/v1/business-chat",json={**body,"tools":["execute_shell"],"tool_consent":True}).status_code==422
    monkeypatch.setenv("META_RUN_BUDGET_CENTS","6");body["tool_consent"]=True
    response=authenticated_client.post("/api/v1/business-chat",json=body)
    assert response.status_code==429,response.text
    saved=authenticated_client.get("/api/v1/business-chat",params={"workspace_id":wid,"thread_id":body["thread_id"]}).json()[0]
    assert [item["status"] for item in saved["tool_results"]]==["completed","failed"]
    assert authenticated_client.post("/api/v1/business-chat",json=body).status_code==409 and len(calls)==1
