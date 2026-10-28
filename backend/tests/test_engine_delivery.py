import json
from uuid import uuid4
from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
from app.main import app
from app import mission_routes
from tests.test_mission_routes import inputs
from tests.test_mission_routes import live_transport
from tests.test_meta_client import png
from app import meta_client
from app.mission import sample_plan
from app.landing import sample_landing
import base64
import httpx
import pytest
from openai import OpenAI


def draft(client):
    body=inputs(client);mission=client.post("/api/v1/missions",json=body).json()
    request={"workspace_id":body["workspace_id"],"request_id":str(uuid4()),"business_name":"Sample Trade Workshop","generation_mode":"sample","generate_visual":True}
    response=client.post(f'/api/v1/missions/{mission["id"]}/prepare',json=request)
    assert response.status_code==201,response.text
    return mission,request,response.json()


def approve(client,request,job):
    scope={"workspace_id":request["workspace_id"]}
    board=client.get(f'/api/v1/campaigns/{job["campaign_id"]}/board',params=scope).json()
    review=next(item for item in board if item["target_kind"]=="landing")
    assert client.post(f'/api/v1/approvals/{review["id"]}/decide',params=scope,json={"decision":"approved","note":"Explicit owner review in offline test"}).status_code==200


@pytest.mark.parametrize("edited",[False,True])
def test_draft_pauses_then_explicit_execution_verifies_and_replays_without_side_effects(authenticated_client,monkeypatch,edited):
    client=authenticated_client;mission,request,job=draft(client)
    scope={"workspace_id":request["workspace_id"]};root=f'/api/v1/missions/{mission["id"]}'
    assert job["awaiting_approval"] is True and job["external_publication"] is False
    assert job["trace"][-1]["kind"]=="human" and job["creative_id"]
    page=client.get(f'/api/v1/landing/{job["page_id"]}',params=scope).json()
    assert not page["published"] and page["spec"]["hero_image_variant_id"]==job["creative_id"]
    if edited:
        response=client.patch(f'/api/v1/landing/{job["page_id"]}',params=scope,json={"spec":{**page["spec"],"headline":"Reviewed workshop inquiry improvement"}})
        assert response.status_code==200,response.text
    assert client.post(root+"/prepare",json=request).json()["id"]==job["id"]
    execute={**scope,"request_id":str(uuid4()),"page_id":job["page_id"],"consent_publish":True,"consent_synthetic_inquiry":True}
    assert client.post(root+"/execute",json=execute).status_code==409
    approve(client,request,job)
    assert not client.get(f'/api/v1/landing/{job["page_id"]}',params=scope).json()["published"]
    assert client.post(root+"/execute",json={**execute,"consent_publish":False}).status_code==422
    monkeypatch.setenv("CORS_ORIGINS","https://sentinelx.example.com");calls=[]
    def public(url,method="GET",body=None):
        calls.append((url,method))
        response=client.get(urlsplit(url).path) if method=="GET" else client.post(urlsplit(url).path,data={k:v[0] for k,v in parse_qs(body.decode()).items()})
        return {"status":response.status_code,"html":response.text}
    monkeypatch.setattr(mission_routes,"request_public",public)
    result=client.post(root+"/execute",json=execute)
    assert result.status_code==200,result.text
    receipt=result.json()
    assert receipt["status"]=="completed" and receipt["external_publication"] is True and receipt["business_impact_measured"] is False
    assert receipt["provenance"]==("user_supplied" if edited else "sample")
    assert receipt["source_mission_provenance"]=="sample"
    assert receipt["verification"]["passed"] is True and len(calls)==2
    assert client.get(f'/api/v1/landing/{job["page_id"]}/leads',params=scope).json()==[]
    assert client.post(root+"/execute",json=execute).json()==receipt and len(calls)==2
    report=client.get(root+"/report",params=scope).json()
    assert len(report["deliveries"])==2
    assert TestClient(app).post(root+"/execute",json=execute).status_code==401
    assert client.post(root+"/prepare",json={**request,"workspace_id":"not-mine"}).status_code==404


def test_failed_verification_proposes_a_new_unapproved_version(authenticated_client,monkeypatch):
    client=authenticated_client;mission,request,job=draft(client);approve(client,request,job)
    scope={"workspace_id":request["workspace_id"]};root=f'/api/v1/missions/{mission["id"]}'
    monkeypatch.setenv("CORS_ORIGINS","https://sentinelx.example.com")
    monkeypatch.setattr(mission_routes,"request_public",lambda *args,**kwargs:{"status":503,"html":"Unavailable"})
    response=client.post(root+"/execute",json={**scope,"request_id":str(uuid4()),"page_id":job["page_id"],"consent_publish":True,"consent_synthetic_inquiry":True})
    assert response.json()["status"]=="failed" and response.json()["external_publication"] is True
    corrected=client.post(root+"/prepare",json={**request,"request_id":str(uuid4()),"correction":True})
    assert corrected.status_code==201,corrected.text
    assert corrected.json()["page_id"]!=job["page_id"] and corrected.json()["awaiting_approval"] is True
    assert not client.get(f'/api/v1/landing/{corrected.json()["page_id"]}',params=scope).json()["published"]


def test_live_design_and_visual_are_budgeted_before_persistence_and_never_publish(authenticated_client,monkeypatch):
    client=authenticated_client;body=inputs(client);live_transport(monkeypatch);calls=[]
    replies=iter([sample_plan(),sample_landing("Trade Workshop","Improve qualified trade inquiries")])
    def send(request):
        calls.append(request)
        if request.url.path.endswith("/images/generations"):
            return httpx.Response(200,json={"created":1,"data":[{"b64_json":base64.b64encode(png()).decode()}]})
        return httpx.Response(200,json={"id":"fixture","object":"chat.completion","created":1,"model":"muse-spark-1.3",
            "choices":[{"index":0,"message":{"role":"assistant","content":json.dumps(next(replies))},"finish_reason":"stop"}]})
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:OpenAI(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(send))))
    mission=client.post("/api/v1/missions",json={**body,"generation_mode":"live","consent_public_fetch":True}).json()
    request={"workspace_id":body["workspace_id"],"request_id":str(uuid4()),"business_name":"Trade Workshop","generation_mode":"live","generate_visual":True}
    response=client.post(f'/api/v1/missions/{mission["id"]}/prepare',json=request)
    assert response.status_code==201,response.text
    assert len(calls)==3 and response.json()["provenance"]=="live_meta" and response.json()["creative_id"]
    page=client.get(f'/api/v1/landing/{response.json()["page_id"]}',params={"workspace_id":body["workspace_id"]}).json()
    assert page["published"] is False
    assert client.post(f'/api/v1/missions/{mission["id"]}/prepare',json=request).json()["id"]==response.json()["id"]
    assert len(calls)==3
