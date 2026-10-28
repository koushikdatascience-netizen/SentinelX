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
                "sha256":"a"*64,"collected_at":"2026-10-28T00:00:00+00:00","html":""}
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
    from app.meta_client import MetaClient
    calls=[]
    monkeypatch.setattr("app.campaign_routes.generation_is_live",lambda *args:True)
    monkeypatch.setattr(MetaClient,"vision",lambda self,*args:{"provenance":"live_meta","model":"muse-spark-1.3","data":"A logo-like brand image."})
    denied=c.post(url,json={"asset_url":"https://example.com/logo.png","analyze_with_meta":True,"consent_to_provider":False})
    assert denied.status_code==422
    allowed=c.post(url,json={"asset_url":"https://example.com/logo.png","analyze_with_meta":True,"consent_to_provider":True})
    assert allowed.status_code==200 and allowed.json()["semantic_review"]["provenance"]=="live_meta"
    saved=c.get(f"/api/v1/intelligence/report/{jid}"+scope).json()["visual_reviews"]
    assert saved[0]["semantic_review"]["text"]=="A logo-like brand image."


def test_visual_asset_batch_uses_one_budgeted_vision_request(authenticated_client,monkeypatch):
    import io
    from PIL import Image
    from app import public_web,site_research
    from tests.test_site_research import HOME
    from app.meta_client import MetaClient
    image=io.BytesIO();Image.new("RGB",(80,40),(128,64,32)).save(image,format="PNG");payload=image.getvalue()
    html=HOME+'<meta property="og:image" content="https://example.com/logo.png"><img src="https://example.com/product.png">'
    fake_site(monkeypatch);original=site_research.request_public
    def pages(url,**kwargs):
        if url.endswith(("logo.png","product.png")):
            return {"url":url,"status":200,"content_type":"image/png","body":payload,"sha256":("a" if url.endswith("logo.png") else "b")*64,
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
    def vision(self,payload,mime,prompt,*args,**kwargs):
        calls.append((payload,mime,prompt));assert mime=="image/jpeg";return {"provenance":"live_meta","model":"muse-spark-1.3","data":"Image 1 and 2 show the same warm wood palette."}
    monkeypatch.setattr(MetaClient,"vision",vision)
    scope="?workspace_id="+wid;path=f"/api/v1/intelligence/research/{jid}/visual-review-batch"+scope
    body={"asset_urls":["https://example.com/logo.png","https://example.com/product.png"],"analyze_with_meta":True,"consent_to_provider":True}
    first=client.post(path,json=body);assert first.status_code==200,first.text
    assert first.json()["provider_requests"]==1 and len(first.json()["images"])==2
    assert first.json()["batch_review"]["image_count"]==2 and len(calls)==1
    reused=client.post(path,json=body);assert reused.status_code==200 and reused.json()["reused"] is True
    assert len(calls)==1


def test_owner_screenshot_batch_is_local_by_default_and_does_not_store_image_bytes(authenticated_client,monkeypatch):
    import io
    from PIL import Image
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
