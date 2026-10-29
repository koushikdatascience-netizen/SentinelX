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


@pytest.mark.parametrize("saved_only",[False,True])
def test_insights_ignore_campaign_quota_and_persist(authenticated_client,monkeypatch,saved_only):
    from tests.test_meta_client import transport,chat
    from app.workspace_store import CampaignQuota
    from app.budget import ApiBudget
    workspace,job_id=enqueue(authenticated_client)
    for name,value in {"MODEL_API_KEY":"offline-test-key","INFERENCE_PROVIDER":"meta",
            "SENTINELX_MODE":"live","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true",
            "CAMPAIGN_WORKSPACE_MAX_ATTEMPTS":"0","META_APP_BUDGET_CENTS":"1000000",
            "META_WORKSPACE_BUDGET_CENTS":"10","META_RUN_BUDGET_CENTS":"10"}.items():
        monkeypatch.setenv(name,value)
    monkeypatch.setattr(research.MetaClient,"search",lambda *args: {"provenance":"live_meta","data":{}})
    finding={"source_id":"O1","quote":"Handmade parts for local businesses.",
        "observation":"The business names its trade audience.","why":"Specific positioning helps visitors assess relevance.",
        "next_step":"Keep the trade audience visible in homepage copy."}
    data={"strengths":[finding],"improvements":[],"unknowns":["Layout was not reviewed from text."]}
    calls=transport(monkeypatch,chat(json.dumps(data)))
    if saved_only:
        with SessionLocal() as db:
            job=db.get(BrandResearchJob,job_id);details=json.loads(job.input_json)
            details["insights_only_job_id"]="previous-evidence";job.input_json=json.dumps(details)
            job.report_json=json.dumps(research.empty_report());db.commit()
    research.execute_job(job_id);research.execute_job(job_id)
    assert len(calls)==1
    with SessionLocal() as db:
        assert db.get(CampaignQuota,workspace) is None
        assert db.get(ApiBudget,"meta").reserved_cents>=5
    report=authenticated_client.get(f"/api/v1/workspaces/{workspace}/business-profile/research").json()[0]["report"]
    assert report["ai_status"]=="ready" and report["insights"]["data"]==research.BrandInsights.model_validate(data).model_dump()


def test_insight_budget_failure_is_clear_and_does_not_call_provider(authenticated_client,monkeypatch):
    from tests.test_meta_client import transport
    workspace,job_id=enqueue(authenticated_client)
    for name,value in {"MODEL_API_KEY":"offline-test-key","INFERENCE_PROVIDER":"meta",
            "SENTINELX_MODE":"live","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true",
            "META_RUN_BUDGET_CENTS":"0"}.items():monkeypatch.setenv(name,value)
    calls=transport(monkeypatch)
    research.execute_job(job_id);research.execute_job(job_id)
    report=authenticated_client.get(f"/api/v1/workspaces/{workspace}/business-profile/research").json()[0]["report"]
    assert calls==[] and report["ai_status"]=="failed"
    assert "budget is exhausted" in report["insight_error"]
    assert "No external request was made" in report["insight_error"]


def test_insight_errors_do_not_expose_provider_details():
    assert "secret-payload" not in research.insight_failure(ValueError("secret-payload"))


def test_source_selection_covers_page_middle_and_end_with_bounded_prompt():
    page={"id":"P1","url":"https://example.org/","title":"Products", "text":"HEAD "*300+"MIDDLE "*600+"CONTACT "*300}
    sources=research.insight_sources({"name":"Workshop"},[page])
    assert all(word in sources[1]["text"] for word in ("HEAD","MIDDLE","CONTACT","[Excerpt gap]"))
    assert "absence" in sources[1]["coverage"]
    assert len(json.dumps({"sources":sources},ensure_ascii=False))<16000
    long_sources=research.insight_sources({"description":"\n"*4000},[{**page,"id":f"P{i}","url":"https://example.org/"+"x"*1950,"text":"\n"*12000} for i in range(4)])
    assert len(json.dumps({"sources":long_sources},ensure_ascii=False))<=15000


def test_report_rejects_empty_findings_and_blank_quotes():
    with pytest.raises(ValueError,match="no supported findings"):
        research.validate_insights({"strengths":[],"improvements":[],"unknowns":["Unknown"]},[])
    finding={"source_id":"P1","quote":" "*10,"observation":"A useful observation.","why":"A reasonable explanation.","next_step":"A specific proposed change."}
    with pytest.raises(ValueError,match="citation"):
        research.validate_insights({"strengths":[finding],"improvements":[],"unknowns":["Unknown"]},[{"id":"P1","text":"Actual content"}])
    finding["quote"]="Before [Excerpt gap] After"
    with pytest.raises(ValueError,match="citation"):
        research.validate_insights({"strengths":[finding],"improvements":[],"unknowns":["Unknown"]},[{"id":"P1","text":finding["quote"]}])


def test_structured_improvement_has_priority_and_verification():
    finding={"source_id":"P1","quote":"Send your drawing for a quote.","observation":"The inquiry has a useful starting point.",
        "why":"The drawing gives the workshop necessary context.","next_step":"Keep the drawing instruction beside the inquiry link.",
        "area":"contact_journey","priority":"medium","verification":"Test that the inquiry link opens on desktop and mobile."}
    result=research.validate_insights({"summary":"Improve the inquiry journey while preserving useful instructions.","strengths":[finding],"improvements":[],"unknowns":["No conversion baseline supplied."]},[{"id":"P1","text":finding["quote"]}])
    assert result["strengths"][0]["verification"]==finding["verification"]
    with pytest.raises(ValueError):
        research.BrandFinding.model_validate({**finding,"priority":"guaranteed_profit"})


def test_failed_saved_report_can_be_explicitly_retried_with_idempotency(authenticated_client,monkeypatch):
    workspace,job_id=enqueue(authenticated_client)
    research.execute_job(job_id)  # Offline evidence run; no inference.
    for name,value in {"MODEL_API_KEY":"offline-test-key","INFERENCE_PROVIDER":"meta",
            "SENTINELX_MODE":"live","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true"}.items():
        monkeypatch.setenv(name,value)
    base=f"/api/v1/workspaces/{workspace}/business-profile/research/{job_id}/insights"
    first=authenticated_client.post(base,json={"request_id":str(uuid4())})
    assert first.status_code==202
    first_id=first.json()["id"]
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,first_id);report=json.loads(job.report_json)
        report["ai_status"]="failed";job.report_json=json.dumps(report);job.state="partial";db.commit()
    body={"request_id":str(uuid4())}
    retry=authenticated_client.post(base,json=body)
    assert retry.status_code==202 and retry.json()["id"]!=first_id
    assert authenticated_client.post(base,json=body).json()["id"]==retry.json()["id"]
    assert authenticated_client.post(base,json={"request_id":str(uuid4())}).json()["id"]==retry.json()["id"]
    assert retry.json()["report"]["insight_sources"]==first.json()["report"]["insight_sources"]
