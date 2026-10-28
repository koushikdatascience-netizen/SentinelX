import json
from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import SessionLocal,utcnow,WorkflowRun
from app.intelligence_store import ResearchJob,BusinessFact
from app.research_jobs import run_job,recover_expired
from tests.test_site_research import fake_site
from tests.test_mission_routes import inputs,live_transport


def begin(client,**extra):
    workspace=inputs(client)["workspace_id"]
    body={"workspace_id":workspace,"request_id":str(uuid4()),"website":"https://example.com/",
        "business_name":"Workshop","consent_public_fetch":True,**extra}
    result=client.post("/api/v1/intelligence/research",json=body)
    assert result.status_code==202,result.text
    return workspace,result.json()["id"],body


def test_persisted_research_facts_review_report_and_safe_action_handoff(authenticated_client,monkeypatch):
    client=authenticated_client;calls=fake_site(monkeypatch);wid,jid,body=begin(client)
    assert calls==[]  # HTTP endpoint queues, it never blocks on crawling.
    assert client.post("/api/v1/intelligence/research",json=body).json()["id"]==jid
    run_job(jid,pause=lambda _:None)
    root="/api/v1/intelligence";scope="?workspace_id="+wid
    job=client.get(root+"/research/"+jid+scope).json()
    assert job["state"]=="completed" and job["page_count"]==3 and job["model_calls"]==0
    facts=client.get(root+"/twin"+scope).json()["facts"]
    social=next(item for item in facts if item["kind"]=="social_profile")
    assert social["verification"]=="source_observed" and social["evidence"]["sha256"]
    reviewed=client.post(root+"/facts/"+social["id"]+"/review"+scope,json={"decision":"owner_confirmed","note":"Owner checked profile identity"})
    assert reviewed.status_code==200 and reviewed.json()["verification"]=="owner_confirmed"
    report=client.get(root+"/report/"+jid+scope).json()
    assert report["summary"]["retrieved_pages"]==3 and report["findings"]
    assert report["summary"]["measured_business_outcomes"] is None
    exported=client.get(root+"/report/"+jid+scope+"&format=html")
    assert exported.status_code==200 and "Content-Security-Policy" in exported.headers
    context=client.post(root+"/research/"+jid+"/prepare-context"+scope).json()
    assert context["id"]==client.post(root+"/research/"+jid+"/prepare-context"+scope).json()["id"]
    assert TestClient(app).get(root+"/twin"+scope).status_code==401
    assert client.get(root+"/research/"+jid+"?workspace_id=foreign").status_code==404
    assert client.post(root+"/facts/"+social["id"]+"/review?workspace_id=foreign",json={"decision":"rejected","note":"Attempted cross-tenant change"}).status_code==404


def test_cancellation_recovery_and_history_have_no_silent_network_retries(authenticated_client,monkeypatch):
    client=authenticated_client;calls=fake_site(monkeypatch);wid,jid,_=begin(client);scope="?workspace_id="+wid
    assert client.post(f"/api/v1/intelligence/research/{jid}/control/cancel"+scope).json()["state"]=="cancelled"
    run_job(jid,pause=lambda _:None);assert calls==[]
    assert client.post(f"/api/v1/intelligence/research/{jid}/control/resume"+scope).json()["state"]=="queued"
    with SessionLocal.begin() as db:
        row=db.get(ResearchJob,jid);row.state="running";row.lease_until=utcnow()-timedelta(seconds=1)
    with SessionLocal.begin() as db:recover_expired(db)
    assert client.get(f"/api/v1/intelligence/research/{jid}"+scope).json()["state"]=="paused" and calls==[]
    assert client.post(f"/api/v1/intelligence/research/{jid}/control/resume"+scope).status_code==200
    run_job(jid,pause=lambda _:None);before=len(calls);run_job(jid,pause=lambda _:None);assert len(calls)==before


def test_research_request_gates_and_idempotency_are_not_bypassed(authenticated_client):
    client=authenticated_client;wid,jid,body=begin(client)
    assert client.post("/api/v1/intelligence/research",json={**body,"business_name":"Changed"}).status_code==409
    assert client.post("/api/v1/intelligence/research",json={**body,"request_id":str(uuid4())}).status_code==429
    assert client.post("/api/v1/intelligence/research",json={**body,"consent_public_fetch":False}).status_code==422
    assert client.post("/api/v1/intelligence/research",json={**body,"website":"http://localhost"}).status_code==422


def test_collected_pages_feed_guarded_mission_without_a_second_crawl(authenticated_client,monkeypatch):
    client=authenticated_client;fake_site(monkeypatch);wid,jid,_=begin(client);run_job(jid,pause=lambda _:None)
    from tests.test_mission_routes import sample_plan
    plan=sample_plan();plan["opportunities"][0]["quote"]="We manufacture wooden components for furniture makers and trade buyers."
    plan["strengths"][0]["quote"]=plan["opportunities"][0]["quote"]
    calls=live_transport(monkeypatch,plan)
    from app import mission_routes
    monkeypatch.setattr(mission_routes,"collect_page",lambda _:(_ for _ in ()).throw(AssertionError("Repeated crawl")))
    result=client.post("/api/v1/missions",json={"workspace_id":wid,"website":"https://example.com/","goal":"Review and improve qualified trade inquiries", "generation_mode":"live","consent_public_fetch":True,"research_job_id":jid})
    assert result.status_code==201,result.text
    assert result.json()["trace"][0]["kind"]=="saved_public_evidence" and len(result.json()["sources"])==3 and len(calls)==1
    sent=json.loads(json.loads(calls[0].content)["messages"][1]["content"])
    assert len(sent["sources"])==3 and sum(len(item["text"]) for item in sent["sources"])<=6000
