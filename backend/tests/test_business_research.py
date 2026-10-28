import io
import json
from datetime import timedelta
from uuid import uuid4
import pytest
from PIL import Image
from app import business_research as research
from app.business_store import BrandResearchJob,BrandAsset
from app.workspace_store import SessionLocal,utcnow
from tests.test_business_onboarding import profile


def enqueue(client,**changes):
    saved=profile(client,**changes);workspace=saved["workspace_id"]
    response=client.post(f"/api/v1/workspaces/{workspace}/business-profile/research",json={"request_id":str(uuid4()),"use_ai":True})
    assert response.status_code==202,response.text
    return workspace,response.json()["id"]


def test_collection_persists_pages_and_screenshots_without_model_calls(authenticated_client,monkeypatch):
    workspace,job_id=enqueue(authenticated_client,website="https://example.org/")
    class Access:
        def get(self,url):return {"url":url,"mime":"text/html","content":b'<title>Workshop</title><h1>We make custom wooden parts.</h1>'}
    out=io.BytesIO();Image.new("RGB",(40,30),"blue").save(out,format="JPEG")
    monkeypatch.setattr(research,"SiteAccess",Access)
    monkeypatch.setattr(research,"screenshots",lambda *args:[{"viewport":"desktop","mime":"image/jpeg","content":out.getvalue(),"clipped":False,"limitation":"test render"}])
    monkeypatch.setattr(research.MetaClient,"_enabled",lambda *args:False)
    monkeypatch.setattr(research.MetaClient,"search",lambda *args:pytest.fail("No paid calls when disabled"))
    research.execute_job(job_id)
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,job_id);report=json.loads(job.report_json)
        assert job.state=="partial" and report["pages"][0]["title"]=="Workshop"
        asset=db.get(BrandAsset,report["pages"][0]["screenshot_ids"][0])
        assert asset.content==out.getvalue() and asset.workspace_id==workspace
    report=authenticated_client.get(f"/api/v1/workspaces/{workspace}/business-profile/research").json()[0]["report"]
    assert report["coverage"]["screenshots_saved"]==1


def test_failed_paid_operations_do_not_repeat_on_idempotent_worker_execution(authenticated_client,monkeypatch):
    workspace,job_id=enqueue(authenticated_client)
    monkeypatch.setenv("MODEL_API_KEY","offline-test-key")
    monkeypatch.setattr(research.MetaClient,"_enabled",lambda *args:True)
    monkeypatch.setattr(research,"claim_attempt",lambda *args:None)
    calls=[]
    def fail(*args,**kwargs):calls.append("request");raise ValueError("provider failed")
    monkeypatch.setattr(research.MetaClient,"search",fail);monkeypatch.setattr(research.MetaClient,"text",fail)
    research.execute_job(job_id);research.execute_job(job_id)
    assert calls==["request","request"]  # one search, one distinct text request; no replay
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,job_id)
        assert job.state=="partial" and json.loads(job.report_json)["insights"] is None


def test_withdrawn_consent_stops_queued_job_and_preserves_state(authenticated_client,monkeypatch):
    workspace,job_id=enqueue(authenticated_client)
    with SessionLocal() as db:db.get(research.BusinessProfile,workspace).consent_at=None;db.commit()
    monkeypatch.setattr(research,"SiteAccess",lambda:pytest.fail("Network must not be constructed"))
    research.execute_job(job_id)
    with SessionLocal() as db:assert db.get(BrandResearchJob,job_id).state=="failed"


def test_recovery_marks_lost_paid_run_interrupted_instead_of_replaying(authenticated_client):
    _,job_id=enqueue(authenticated_client)
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,job_id);job.state="running";job.lease_until=utcnow()-timedelta(seconds=10);db.commit()
        research.recover_jobs(db)
        db.expire_all();assert db.get(BrandResearchJob,job_id).state=="interrupted"


def test_model_insights_require_matching_source_quotes():
    finding={"source_id":"P1","quote":"We make custom parts.","observation":"The workshop has a clear offer.","why":"The source states what the workshop produces.","next_step":"Keep this useful offer visible on the homepage."}
    data={"strengths":[finding],"improvements":[],"unknowns":["No sales data supplied."]}
    assert research.validate_insights(data,[{"id":"P1","text":"We make custom parts."}])["strengths"]
    with pytest.raises(ValueError):research.validate_insights(data,[{"id":"P1","text":"Another company"}])
