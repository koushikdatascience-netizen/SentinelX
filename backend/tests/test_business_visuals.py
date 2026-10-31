import io
import json
from uuid import uuid4
import pytest
from PIL import Image
from app import business_research as research,business_visuals as visuals
from app.business_store import BrandResearchJob,BrandAsset
from app.business_files import store_asset
from app.workspace_store import SessionLocal
from tests.test_business_onboarding import profile


def png(color):
    out=io.BytesIO();Image.new("RGB",(100,120),color).save(out,format="PNG");return out.getvalue()


def saved_source(client):
    workspace=profile(client)["workspace_id"]
    item=client.post(f"/api/v1/workspaces/{workspace}/business-profile/research",json={"request_id":str(uuid4()),"use_ai":False}).json()
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,item["id"]);job.state="partial"
        asset=store_asset(db,workspace,"screenshot","home-desktop.png","image/png",png("blue"),source_url="https://example.org/",job_id=job.id,metadata={"viewport":"desktop"})
        report=research.empty_report();report["pages"]=[{"id":"P1","text":"Custom parts in bulk.","url":"https://example.org/","screenshot_ids":[asset.id]}]
        report["insights"]={"provenance":"live_meta","data":{"summary":"Existing saved text report","competitor_comparisons":[{"name":"Candidate","url":"https://candidate.example/"}]}}
        report["ai_status"]="ready";job.report_json=json.dumps(report);db.commit()
        return workspace,job.id,asset.id


def enable(monkeypatch):
    for name,value in {"MODEL_API_KEY":"offline-test-key","INFERENCE_PROVIDER":"meta","SENTINELX_MODE":"live",
            "ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true","META_APP_BUDGET_CENTS":"1000000",
            "META_WORKSPACE_BUDGET_CENTS":"30","META_RUN_BUDGET_CENTS":"30","CAMPAIGN_WORKSPACE_MAX_ATTEMPTS":"0"}.items():monkeypatch.setenv(name,value)


def output(count=1):
    return {"summary":"The visible layout can better highlight the product and next step.","findings":[{"image_index":i,"area":"layout","priority":"medium",
        "observation":"The visible product and contact areas compete for attention.","suggested_improvement":"Give the product heading more space and align the inquiry action.",
        "why":"A clearer visual hierarchy makes the primary action easier to locate.","verification":"Review the draft at desktop and phone widths.",
        "regeneration_prompt":"Prepare an original page design concept with a clear product hierarchy and one primary inquiry action."} for i in range(1,count+1)]}


def test_saved_visual_report_is_one_budgeted_http_call_without_recollection_and_survives_reload(authenticated_client,monkeypatch):
    from tests.test_meta_client import transport,chat
    workspace,source_id,asset_id=saved_source(authenticated_client);enable(monkeypatch)
    calls=transport(monkeypatch,chat(json.dumps(output())))
    monkeypatch.setattr(research,"SiteAccess",lambda:pytest.fail("No recollection"))
    monkeypatch.setattr(visuals,"SiteAccess",lambda:pytest.fail("No candidate selected"))
    monkeypatch.setattr(research.MetaClient,"text",lambda *a:pytest.fail("No text request"))
    monkeypatch.setattr(research.MetaClient,"search",lambda *a:pytest.fail("No search request"))
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights"
    body={"request_id":str(uuid4()),"consent":True}
    first=authenticated_client.post(path,json=body);assert first.status_code==202,first.text
    assert authenticated_client.post(path,json=body).json()["id"]==first.json()["id"]
    research.execute_job(first.json()["id"]);research.execute_job(first.json()["id"])
    assert len(calls)==1
    with SessionLocal() as db:
        report=json.loads(db.get(BrandResearchJob,first.json()["id"]).report_json)
        assert report["ai_status"]=="ready" and report["insights"]["data"]["summary"]=="Existing saved text report"
        assert report["visual_status"]=="ready" and report["visual_review"]["data"]==output()
        assert report["visual_review"]["panels"][0]["asset_id"]==asset_id
        assert json.loads(db.get(BrandResearchJob,source_id).report_json)["visual_review"] is None
    reloaded=authenticated_client.get(f"/api/v1/workspaces/{workspace}/business-profile/research").json()[0]
    assert reloaded["report"]["visual_status"]=="ready"
    assert authenticated_client.post(path,json={"request_id":str(uuid4()),"consent":True}).json()["id"]==first.json()["id"]


def test_visual_route_requires_consent_owner_scope_and_evidenced_candidate(authenticated_client,monkeypatch):
    workspace,source_id,_=saved_source(authenticated_client);enable(monkeypatch)
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights"
    body={"request_id":str(uuid4()),"consent":True}
    assert authenticated_client.post(path,json={**body,"consent":False}).status_code==422
    assert authenticated_client.post(path,json={**body,"competitor_url":"https://arbitrary.example/"}).status_code==422
    other=profile(authenticated_client)["workspace_id"]
    assert authenticated_client.post(path.replace(workspace,other),json=body).status_code==404
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    assert authenticated_client.post(path,json=body).status_code==503


@pytest.mark.parametrize("failure",["mapping","http","integrity","budget"])
def test_failed_visual_request_does_not_replay_or_replace_text(authenticated_client,monkeypatch,failure):
    from tests.test_meta_client import transport,chat
    workspace,source_id,asset_id=saved_source(authenticated_client);enable(monkeypatch)
    data=output()
    if failure=="mapping":data["findings"][0]["image_index"]=2
    calls=transport(monkeypatch,chat(json.dumps(data)) if failure!="http" else {"error":{"message":"private-payload"}},status=502 if failure=="http" else 200)
    if failure=="integrity":
        with SessionLocal() as db:db.get(BrandAsset,asset_id).sha256="0"*64;db.commit()
    if failure=="budget":monkeypatch.setenv("META_RUN_BUDGET_CENTS","0")
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights"
    result=authenticated_client.post(path,json={"request_id":str(uuid4()),"consent":True});assert result.status_code==202
    job_id=result.json()["id"];research.execute_job(job_id);research.execute_job(job_id)
    assert len(calls)==(0 if failure in {"integrity","budget"} else 1)
    with SessionLocal() as db:
        report=json.loads(db.get(BrandResearchJob,job_id).report_json)
        assert report["visual_status"]=="failed" and report["visual_review"] is None
        assert report["insights"]["data"]["summary"]=="Existing saved text report"
        assert "private-payload" not in report["visual_error"]


def test_candidate_capture_is_explicit_and_maps_business_and_candidate_panels(authenticated_client,monkeypatch):
    workspace,source_id,asset_id=saved_source(authenticated_client);enable(monkeypatch);captures=[]
    class Access:
        def get(self,url):captures.append(url);return {"url":url,"mime":"text/html","content":b"<h1>Candidate</h1>"}
    monkeypatch.setattr(visuals,"SiteAccess",Access)
    monkeypatch.setattr(visuals,"screenshots",lambda *a:[{"viewport":"desktop","mime":"image/png","content":png("red"),"clipped":False,"limitation":"Mocked candidate render"}])
    monkeypatch.setattr(visuals.MetaClient,"vision",lambda *a:{"provenance":"live_meta","data":output(2)})
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights"
    response=authenticated_client.post(path,json={"request_id":str(uuid4()),"consent":True,"competitor_url":"https://candidate.example/"})
    assert response.status_code==202;research.execute_job(response.json()["id"])
    with SessionLocal() as db:
        report=json.loads(db.get(BrandResearchJob,response.json()["id"]).report_json)
        assert report["visual_status"]=="ready"
        assert [p["role"] for p in report["visual_review"]["panels"]]==["business","competitor_candidate"]
        assert report["visual_review"]["comparison_url"]=="https://candidate.example/"
    assert captures==["https://candidate.example/"]


def test_visual_brief_generation_links_owned_report_and_rejects_unrelated_sources(authenticated_client,monkeypatch):
    import base64
    from app import workbench
    workspace,source_id,asset_id=saved_source(authenticated_client);enable(monkeypatch)
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,source_id);report=json.loads(job.report_json)
        report["visual_review"]={"provenance":"live_meta","data":output(),"panels":[{"asset_id":asset_id,"role":"business"}]}
        job.report_json=json.dumps(report);db.commit()
    monkeypatch.setattr(workbench,"claim_attempt",lambda *a:None)
    monkeypatch.setattr(workbench.MetaClient,"image",lambda *a:{"provenance":"live_meta","model":"offline-image","data":{"b64_json":base64.b64encode(png("green")).decode(),"format":"png"}})
    body={"workspace_id":workspace,"request_id":str(uuid4()),"tool":"image","prompt":"Make an original visual concept from the reviewed design brief.","asset_id":asset_id,"source_visual_job_id":source_id}
    result=authenticated_client.post("/api/v1/workbench",json=body)
    assert result.status_code==201,result.text
    assert result.json()["source_asset_id"]==asset_id and result.json()["source_visual_job_id"]==source_id
    assert "not a pixel-preserving edit" in result.json()["limitation"]
    assert authenticated_client.post("/api/v1/workbench",json={**body,"request_id":str(uuid4()),"asset_id":"foreign"}).status_code==404


def test_visual_request_id_conflict_and_failed_retry_are_explicit(authenticated_client,monkeypatch):
    workspace,source_id,_=saved_source(authenticated_client);enable(monkeypatch)
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights"
    body={"request_id":str(uuid4()),"consent":True}
    first=authenticated_client.post(path,json=body);assert first.status_code==202
    assert authenticated_client.post(path,json={**body,"competitor_url":"https://candidate.example/"}).status_code==409
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,first.json()["id"]);job.state="partial";report=json.loads(job.report_json)
        report["visual_status"]="failed";job.report_json=json.dumps(report);db.commit()
    retry=authenticated_client.post(path,json={"request_id":str(uuid4()),"consent":True})
    assert retry.status_code==202 and retry.json()["id"]!=first.json()["id"]


def test_foreign_screenshot_references_are_not_selected(authenticated_client):
    workspace,source_id,asset_id=saved_source(authenticated_client)
    other=profile(authenticated_client)["workspace_id"]
    with SessionLocal() as db:
        assert visuals.select_assets(db,other,{"pages":[{"screenshot_ids":[asset_id]}]})==[]


def test_visually_identical_normalized_images_are_reviewed_once(authenticated_client,monkeypatch):
    workspace,source_id,_=saved_source(authenticated_client);enable(monkeypatch);calls=[]
    # Different PNG metadata changes the original hash but not pixels or normalized JPEG.
    from PIL.PngImagePlugin import PngInfo
    with Image.open(io.BytesIO(png("blue"))) as original:
        info=PngInfo();info.add_text("capture","second page");out=io.BytesIO();original.save(out,format="PNG",pnginfo=info)
    with SessionLocal() as db:
        job=db.get(BrandResearchJob,source_id);report=json.loads(job.report_json)
        other=store_asset(db,workspace,"screenshot","same-pixels.png","image/png",out.getvalue(),job_id=job.id,metadata={"viewport":"mobile"})
        report["pages"][0]["screenshot_ids"].append(other.id);job.report_json=json.dumps(report);db.commit();duplicate=other.id
    def vision(self,*args):calls.append(1);return {"provenance":"live_meta","data":output()}
    monkeypatch.setattr(visuals.MetaClient,"vision",vision)
    response=authenticated_client.post(f"/api/v1/workspaces/{workspace}/business-profile/research/{source_id}/visual-insights",json={"request_id":str(uuid4()),"consent":True})
    research.execute_job(response.json()["id"]);research.execute_job(response.json()["id"])
    with SessionLocal() as db:
        report=json.loads(db.get(BrandResearchJob,response.json()["id"]).report_json)
        assert report["visual_status"]=="ready",report["visual_error"]
        assert report["visual_review"]["duplicate_asset_ids"]==[duplicate]
        assert len(report["visual_review"]["panels"])==1 and calls==[1]


def test_visual_diagnostics_are_specific_and_never_expose_payloads():
    assert "panel" in research.insight_failure(visuals.VisualReportError("mapping"))
    assert "No vision request" in research.insight_failure(visuals.VisualReportError("integrity"))
    assert "private-payload" not in research.insight_failure(ValueError("private-payload"))
