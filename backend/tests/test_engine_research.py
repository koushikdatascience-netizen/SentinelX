import json
import httpx
from openai import OpenAI
from app import meta_client,mission_routes
from app.mission import sample_source,sample_plan
from app.mission_research import sample_research
from tests.test_mission_routes import inputs,live_transport
from tests.test_engine_inputs import grounded


def test_discovery_context_and_research_reach_the_planner_with_bounded_calls(authenticated_client,monkeypatch):
    client=authenticated_client;body=inputs(client);live_transport(monkeypatch)
    note=client.post("/api/v1/business-context",data={"workspace_id":body["workspace_id"],"notes":"Trade components only; preserve minimum quantities and the owner's order process.","consent":"true"}).json()
    source=sample_source();source.pop("id",None);source.pop("role",None);urls=[]
    def collect(url):urls.append(url);return {**source,"url":url,"origin":"retrieved_public_page","sha256":"0"*64}
    monkeypatch.setattr(mission_routes,"collect_page",collect)
    calls=[];chat_replies=iter([sample_research(),sample_plan()])
    def send(request):
        calls.append(request)
        if request.url.path=="/v1/responses":return httpx.Response(200,json=grounded())
        return httpx.Response(200,json={"id":"fixture","object":"chat.completion","created":1,"model":"muse-spark-1.3",
            "choices":[{"index":0,"message":{"role":"assistant","content":json.dumps(next(chat_replies))},"finish_reason":"stop"}]})
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:OpenAI(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(send))))
    body.update(generation_mode="live",consent_public_fetch=True,discover_market=True,research_handoff=True,context_ids=[note["id"]])
    result=client.post("/api/v1/missions",json=body)
    assert result.status_code==201,result.text
    data=result.json()
    assert len(calls)==3 and len(urls)==2 and data["market_research"]["data"]["searched"] is True
    assert data["sources"][1]["role"]=="discovered_candidate" and data["sources"][1]["id"]=="S2"
    planner=json.loads(calls[-1].content)
    context=json.loads(planner["messages"][1]["content"])
    assert context["business_context_unverified"][0]["id"]==note["id"]
    assert context["validated_research"]["validated"] is True
    assert len(planner["messages"][1]["content"])<=16000
    client.post("/api/v1/missions",json=body)
    assert len(calls)==3
