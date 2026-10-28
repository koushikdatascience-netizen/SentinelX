import json
import hashlib
import io
from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from PIL import Image
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


def _visual_screenshot_job(client,monkeypatch):
    fake_site(monkeypatch);wid,jid,_=begin(client);run_job(jid,pause=lambda _:None)
    image=io.BytesIO();Image.new("RGB",(120,80),(20,80,160)).save(image,format="PNG")
    path=f"/api/v1/intelligence/research/{jid}/visual-screenshot-batch"
    files=[("files",("public-page.png",image.getvalue(),"image/png"))]
    return wid,jid,path,files


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


def test_explicit_visual_review_measures_selected_site_asset_and_sends_only_with_consent(authenticated_client,monkeypatch):
    import io
    from PIL import Image
    from app import public_web
    from tests.test_site_research import HOME
    image=io.BytesIO();Image.new("RGB",(80,40),(128,64,32)).save(image,format="PNG");payload=image.getvalue()
    html=HOME+'<meta property="og:image" content="https://example.com/logo.png">'
    fake_site(monkeypatch)
    from app import site_research
    original=site_research.request_public
    def pages_and_asset(url,**kwargs):
        if url.endswith("logo.png"):
            assert kwargs["same_host"]=="example.com"
            return {"url":url,"status":200,"content_type":"image/png","body":payload,
                "sha256":hashlib.sha256(payload).hexdigest(),"collected_at":"2026-10-28T00:00:00+00:00","html":""}
        if url.endswith("/"):
            response=original(url,**kwargs) if False else {"url":url,"html":html,"status":200,
                "sha256":"b"*64,"bytes":len(html),"collected_at":"2026-10-28T00:00:00+00:00"}
            return response
        return original(url,**kwargs)
    def asset_transport(url,**kwargs):
        if url.endswith("robots.txt"):
            return {"url":url,"status":404,"content_type":"text/plain","html":"","body":b"",
                "sha256":"c"*64,"collected_at":"2026-10-28T00:00:00+00:00"}
        return pages_and_asset(url,**kwargs)
    monkeypatch.setattr(site_research,"request_public",pages_and_asset)
    monkeypatch.setattr(public_web,"request_public",asset_transport)
    c=authenticated_client;wid,jid,_=begin(c);run_job(jid,pause=lambda _:None);scope="?workspace_id="+wid
    url=f"/api/v1/intelligence/research/{jid}/visual-review"+scope
    bad=c.post(url,json={"asset_url":"https://example.com/not-listed.png"})
    assert bad.status_code==422
    local=c.post(url,json={"asset_url":"https://example.com/logo.png"})
    assert local.status_code==200 and local.json()["local_visual_measurements"]["dominant_colors"][0]=="#804020"
    assert local.json()["semantic_review"] is None and local.json()["input_provenance"]=="retrieved_public_asset"
    denied=c.post(url,json={"asset_url":"https://example.com/logo.png","analyze_with_meta":True,"consent_to_provider":False})
    assert denied.status_code==409 and "visual-review-batch" in denied.text
    allowed=c.post(url,json={"asset_url":"https://example.com/logo.png","analyze_with_meta":True,"consent_to_provider":True})
    assert allowed.status_code==409 and "visual-review-batch" in allowed.text
    saved=c.get(f"/api/v1/intelligence/report/{jid}"+scope).json()["visual_reviews"]
    assert saved[0]["semantic_review"] is None


def test_visual_asset_batch_uses_one_budgeted_vision_request(authenticated_client,monkeypatch):
    import io
    from PIL import Image
    from app import public_web,site_research
    from tests.test_site_research import HOME
    from app.meta_client import MetaClient
    image=io.BytesIO();Image.new("RGB",(80,40),(128,64,32)).save(image,format="PNG");payload=image.getvalue()
    other=io.BytesIO();Image.new("RGB",(80,40),(64,128,32)).save(other,format="PNG");product_payload=other.getvalue()
    html=HOME+'<meta property="og:image" content="https://example.com/logo.png"><img src="https://example.com/product.png">'
    fake_site(monkeypatch);original=site_research.request_public
    def pages(url,**kwargs):
        if url.endswith(("logo.png","product.png")):
            image_bytes=product_payload if url.endswith("product.png") else payload
            return {"url":url,"status":200,"content_type":"image/png","body":image_bytes,"sha256":hashlib.sha256(image_bytes).hexdigest(),
                "collected_at":"2026-10-28T00:00:00+00:00","html":""}
        if url.endswith("/"):
            return {"url":url,"html":html,"status":200,"sha256":"c"*64,"bytes":len(html),"collected_at":"2026-10-28T00:00:00+00:00"}
        return original(url,**kwargs)
    def transport(url,**kwargs):
        if url.endswith("robots.txt"):
            return {"url":url,"status":404,"content_type":"text/plain","html":"","body":b"","sha256":"d"*64,"collected_at":"2026-10-28T00:00:00+00:00"}
        return pages(url,**kwargs)
    monkeypatch.setattr(site_research,"request_public",pages);monkeypatch.setattr(public_web,"request_public",transport)
    client=authenticated_client;wid,jid,_=begin(client);run_job(jid,pause=lambda _:None)
    monkeypatch.setattr("app.campaign_routes.generation_is_live",lambda *args:True)
    calls=[]
    def vision(self,payload,mime,prompt,json_schema=None):
        calls.append((payload,mime,prompt,json_schema));assert mime=="image/jpeg";assert json_schema["properties"]["findings"]["minItems"]==2
        return {"provenance":"live_meta","model":"muse-spark-1.3","data":{"findings":[
            {"image_index":1,"observation":"Logo panel uses a warm wood palette.","suggested_improvement":"Keep the logo panel uncropped."},
            {"image_index":2,"observation":"Product panel shows a turned wood profile.","suggested_improvement":"Add a clear product-size reference."}],
            "summary":"The two selected panels share warm brown tones."}}
    monkeypatch.setattr(MetaClient,"vision",vision)
    scope="?workspace_id="+wid;path=f"/api/v1/intelligence/research/{jid}/visual-review-batch"+scope
    body={"asset_urls":["https://example.com/logo.png","https://example.com/product.png"],"analyze_with_meta":True,"consent_to_provider":True}
    denied=client.post(path,json={**body,"consent_to_provider":False});assert denied.status_code==422 and calls==[]
    foreign=client.post(path.replace(wid,str(uuid4())),json=body);assert foreign.status_code==404 and calls==[]
    first=client.post(path,json=body);assert first.status_code==200,first.text
    assert first.json()["provider_requests"]==1 and len(first.json()["images"])==2
    assert first.json()["batch_review"]["image_count"]==2 and len(calls)==1
    assert first.json()["images"][0]["visual_finding"]["observation"]=="Logo panel uses a warm wood palette."
    assert first.json()["images"][1]["visual_finding"]["suggested_improvement"]=="Add a clear product-size reference."
    assert first.json()["batch_review"]["summary"]=="The two selected panels share warm brown tones."
    reused=client.post(path,json=body);assert reused.status_code==200 and reused.json()["reused"] is True
    assert len(calls)==1
    persisted=client.get(f"/api/v1/intelligence/report/{jid}"+scope).json()["visual_batches"][0]
    assert persisted["images"][0]["visual_finding"]["image_index"]==1
    assert persisted["batch_review"]["summary"]=="The two selected panels share warm brown tones."


def test_owner_screenshot_batch_is_local_by_default_and_does_not_store_image_bytes(authenticated_client,monkeypatch):
    image=io.BytesIO();Image.new("RGB",(120,80),(20,80,160)).save(image,format="PNG");payload=image.getvalue()
    client=authenticated_client;fake_site(monkeypatch)
    wid,jid,_=begin(client)
    run_job(jid,pause=lambda _:None)
    response=client.post(f"/api/v1/intelligence/research/{jid}/visual-screenshot-batch",params={"workspace_id":wid},
        files=[("files",("homepage.png",payload,"image/png"))])
    assert response.status_code==200,response.text
    result=response.json();assert result["provider_requests"]==0
    assert result["images"][0]["source"]=="owner_supplied_screenshot"
    assert result["images"][0]["local_visual_measurements"]["width"]==120
    assert "body" not in result["images"][0] and "contact_sheet" not in result


def _enable_fake_paid_meta(monkeypatch):
    for key,value in {"INFERENCE_PROVIDER":"meta","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true",
        "SENTINELX_MODE":"live","MODEL_API_KEY":"test-only-not-a-real-key","META_MODEL":"muse-spark-1.3",
        "META_APP_BUDGET_CENTS":"1000000","META_WORKSPACE_BUDGET_CENTS":"1000000","META_RUN_BUDGET_CENTS":"5"}.items():
        monkeypatch.setenv(key,value)


def _structured_findings(count,duplicate=False):
    indices=[1,1] if duplicate and count==2 else list(range(1,count+1))
    return {"findings":[{"image_index":index,"observation":f"Panel {index} shows a visible product detail.",
        "suggested_improvement":f"Use panel {index} with a specific, factual caption."} for index in indices],
        "summary":"The selected panels show product visuals with related colors."}


def test_budget_rejection_makes_no_request_and_can_be_retried(authenticated_client,monkeypatch):
    from tests.test_meta_client import chat,transport
    from app.budget import ApiBudget
    from app.workspace_store import WorkflowRun
    from sqlalchemy import select
    client=authenticated_client;wid,jid,path,files=_visual_screenshot_job(client,monkeypatch)
    _enable_fake_paid_meta(monkeypatch);monkeypatch.setenv("META_RUN_BUDGET_CENTS","0")
    response_payload=chat(json.dumps(_structured_findings(1)))
    calls=transport(monkeypatch,response_payload)
    def reserved(scope):
        with SessionLocal() as db:return db.scalar(select(ApiBudget.reserved_cents).where(ApiBudget.provider==scope)) or 0
    app_scope_before=reserved("meta")
    workspace_scope="mw:"+hashlib.sha256(wid.encode()).hexdigest()[:32]
    workspace_scope_before=reserved(workspace_scope)
    scope={"workspace_id":wid}
    form={"analyze_with_meta":"true","consent_to_provider":"true"}
    blocked=client.post(path,params=scope,data=form,files=files)
    assert blocked.status_code==429 and "Meta budget reached" in blocked.text
    assert calls==[]
    assert reserved("meta")==app_scope_before and reserved(workspace_scope)==workspace_scope_before
    monkeypatch.setenv("META_RUN_BUDGET_CENTS","5")
    success=client.post(path,params=scope,data=form,files=files)
    assert success.status_code==200,success.text
    assert len(calls)==1 and success.json()["provider_requests"]==1
    request_body=json.loads(calls[0].content)
    output_schema=request_body["response_format"]["json_schema"]["schema"]
    assert output_schema["properties"]["findings"]["minItems"]==1
    assert output_schema["properties"]["findings"]["items"]["properties"]["image_index"]["enum"]==[1]
    assert output_schema["required"]==["findings","summary"]
    cached=client.post(path,params=scope,data=form,files=files)
    assert cached.status_code==200 and cached.json()["reused"] is True
    assert len(calls)==1
    assert reserved("meta")==app_scope_before+5
    assert reserved(workspace_scope)==workspace_scope_before+5
    with SessionLocal() as db:
        paid_run=db.scalar(select(WorkflowRun).where(WorkflowRun.workspace_id==wid,
            WorkflowRun.objective=="Visual contact-sheet review · 1 images").order_by(WorkflowRun.created_at.desc()))
    run_scope="mr:"+hashlib.sha256((wid+":"+paid_run.id).encode()).hexdigest()[:32]
    assert reserved(run_scope)==5
    persisted=client.get(f"/api/v1/intelligence/report/{jid}",params={"workspace_id":wid}).json()["visual_batches"][0]
    assert persisted["images"][0]["visual_finding"]["image_index"]==1
    assert persisted["batch_review"]["summary"]==_structured_findings(1)["summary"]


def test_malformed_paid_visual_response_fails_clearly_and_is_not_retried(authenticated_client,monkeypatch):
    from tests.test_meta_client import chat,transport
    from app.budget import ApiBudget
    from sqlalchemy import select
    client=authenticated_client;wid,jid,path,files=_visual_screenshot_job(client,monkeypatch)
    _enable_fake_paid_meta(monkeypatch)
    calls=transport(monkeypatch,chat(json.dumps(_structured_findings(2,duplicate=True))))
    scope={"workspace_id":wid};form={"analyze_with_meta":"true","consent_to_provider":"true"}
    # Two panels are needed to exercise duplicate panel indices; add a second screenshot.
    distinct=io.BytesIO();Image.new("RGB",(120,80),(80,120,20)).save(distinct,format="PNG")
    files.append(("files",("public-page-2.png",distinct.getvalue(),"image/png")))
    failed=client.post(path,params=scope,data=form,files=files)
    assert failed.status_code==502 and "invalid numbered visual findings" in failed.text
    retried=client.post(path,params=scope,data=form,files=files)
    assert retried.status_code==409 and len(calls)==1
    workspace_scope="mw:"+hashlib.sha256(wid.encode()).hexdigest()[:32]
    with SessionLocal() as db:reserved=db.scalar(select(ApiBudget.reserved_cents).where(ApiBudget.provider==workspace_scope)) or 0
    assert reserved==5
    report=client.get(f"/api/v1/intelligence/report/{jid}",params={"workspace_id":wid}).json()
    assert report["visual_batches"]==[]


def test_paid_provider_http_failure_is_not_retried(authenticated_client,monkeypatch):
    from tests.test_meta_client import transport
    client=authenticated_client;wid,jid,path,files=_visual_screenshot_job(client,monkeypatch)
    _enable_fake_paid_meta(monkeypatch)
    calls=transport(monkeypatch,{"error":{"message":"private transport details"}},status=500)
    scope={"workspace_id":wid};form={"analyze_with_meta":"true","consent_to_provider":"true"}
    failed=client.post(path,params=scope,data=form,files=files)
    assert failed.status_code==502 and "stopped without retry" in failed.text
    retry=client.post(path,params=scope,data=form,files=files)
    assert retry.status_code==409 and len(calls)==1
    assert "private transport details" not in failed.text


def test_social_search_requires_linked_profile_consent_and_reuses_saved_result(authenticated_client,monkeypatch):
    from app.meta_client import MetaClient
    fake_site(monkeypatch);client=authenticated_client;wid,jid,_=begin(client);run_job(jid,pause=lambda _:None)
    monkeypatch.setenv("SENTINELX_MODE","live");monkeypatch.setenv("INFERENCE_PROVIDER","meta")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true");monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL","true");monkeypatch.setenv("MODEL_API_KEY","test-only-mock")
    calls=[]
    def search(self,query,purpose="market"):
        calls.append((query,purpose))
        return {"provenance":"live_meta","model":"muse-spark-1.3","data":{"summary":"Two public posts mention custom furniture.","citations":[{"url":"https://instagram.com/p/example","title":"Public post"}],"results":[],"searched":True}}
    monkeypatch.setattr(MetaClient,"search",search)
    scope="?workspace_id="+wid;path=f"/api/v1/intelligence/research/{jid}/social-search"+scope
    consent={"profile_url":"https://instagram.com/workshop","consent_public_search":True}
    assert client.post(path,json={**consent,"profile_url":"https://instagram.com/other"}).status_code==422
    first=client.post(path,json=consent);assert first.status_code==200,first.text
    second=client.post(path,json=consent);assert second.status_code==200 and second.json()["reused"] is True
    assert len(calls)==1 and calls[0][1]=="social"
