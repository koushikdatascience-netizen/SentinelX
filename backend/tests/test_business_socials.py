import json
from uuid import uuid4
import httpx
import pytest
from openai import OpenAI as SDK
from app import business_socials as socials,business_research as research,meta_client
from app.business_store import BrandResearchJob
from app.workspace_store import SessionLocal
from tests.test_business_onboarding import profile
from tests.test_business_visuals import enable
from tests.test_meta_client import chat
from tests.test_engine_inputs import grounded

URL="https://instagram.com/workshop"


def result():
    return {"platforms":[{"url":URL,"platform":"instagram","coverage":"indexed_profile_evidence","summary":"The indexed profile names the custom product offering.",
        "findings":[{"source_id":"S1.W1","quote":"Custom wooden parts in Kalyani.","observation":"The indexed profile identifies the product offering.","change":"Test a clearer quote invitation beside the product explanation.","why":"A specific next step may help trade buyers send a complete inquiry.","verification":"Review qualified inquiries against a dated baseline."}],
        "competitor_examples":[],"experiments":[{"format":"Reel","topic":"Show the custom order process","hook":"What should you send with a workshop inquiry?","call_to_action":"Send your drawing and quantity.","measure":"Count inquiries containing a design, quantity and date; no uplift is assumed."}],"unknowns":["Full feed and private analytics were not accessed; growth is unmeasured."]}]}


def sources():
    return [{"id":"S1.W1","url":URL,"profile_url":URL,"text":"Workshop\nCustom wooden parts in Kalyani.","origin":"search_pointer"}]


def test_social_findings_are_platform_mapped_and_do_not_treat_other_profiles_as_owner():
    selected=[{"platform":"instagram","url":URL}]
    assert socials.validate_report(result(),selected,sources())["platforms"]
    wrong=result();wrong["platforms"][0]["platform"]="facebook"
    with pytest.raises(ValueError,match="mapping"):socials.validate_report(wrong,selected,sources())
    foreign=[{**sources()[0],"url":"https://instagram.com/competitor"}]
    with pytest.raises(ValueError,match="profile"):socials.validate_report(result(),selected,foreign)
    wrong=result();wrong["platforms"][0]["findings"][0]["quote"]="An invented successful campaign"
    with pytest.raises(ValueError,match="citation"):socials.validate_report(wrong,selected,sources())
    assert not socials.same_profile("https://instagram.com/workshop2",URL)
    assert not socials.same_profile("https://facebook.com/profile.php?id=456","https://facebook.com/profile.php?id=123")


def test_social_only_business_runs_one_budgeted_search_plus_synthesis_and_reuses_request(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client,socials=[{"platform":"instagram","url":URL}])["workspace_id"];enable(monkeypatch);calls=[]
    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/responses"):
            payload=grounded();payload["output"][0]["results"][0].update(url=URL,title="Workshop",snippet="Custom wooden parts in Kalyani.")
            payload["output"][1]["content"][0]["annotations"]=[]
            return httpx.Response(200,json=payload)
        return httpx.Response(200,json=chat(json.dumps(result())))
    def factory(**kwargs):
        assert kwargs["max_retries"]==0
        return SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(meta_client,"OpenAI",factory)
    monkeypatch.setattr(research,"SiteAccess",lambda:pytest.fail("Social research does not crawl a website or platform"))
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/profile/social-insights"
    body={"request_id":str(uuid4()),"urls":[URL],"context":"Improve trade inquiries; no analytics baseline supplied.","consent":True}
    first=authenticated_client.post(path,json=body);assert first.status_code==202,first.text
    assert authenticated_client.post(path,json=body).json()["id"]==first.json()["id"]
    research.execute_job(first.json()["id"]);research.execute_job(first.json()["id"])
    assert len(calls)==2
    with SessionLocal() as db:
        report=json.loads(db.get(BrandResearchJob,first.json()["id"]).report_json)
        assert report["social_research"]["status"]=="ready"
        assert report["social_research"]["report"]["data"]==result()
    loaded=authenticated_client.get(f"/api/v1/workspaces/{workspace}/business-profile/research").json()[0]
    assert loaded["report"]["social_research"]["sources"][0]["profile_url"]==URL


def test_social_research_rejects_unsaved_profiles_missing_consent_and_foreign_workspace(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client,socials=[{"platform":"instagram","url":URL}])["workspace_id"];enable(monkeypatch)
    path=f"/api/v1/workspaces/{workspace}/business-profile/research/profile/social-insights"
    body={"request_id":str(uuid4()),"urls":[URL],"consent":True}
    assert authenticated_client.post(path,json={**body,"consent":False}).status_code==422
    assert authenticated_client.post(path,json={**body,"urls":["https://instagram.com/arbitrary"]}).status_code==422
    assert authenticated_client.post(path,json={**body,"urls":[URL,URL]}).status_code==422
    assert authenticated_client.post(path.replace(workspace,"foreign"),json=body).status_code==404
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    assert authenticated_client.post(path,json=body).status_code==503


def test_failed_social_search_does_not_pay_for_synthesis_or_replay(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client,socials=[{"platform":"instagram","url":URL}])["workspace_id"];enable(monkeypatch);calls=[]
    def fail(*a):calls.append(1);raise ValueError("private-payload")
    monkeypatch.setattr(socials.MetaClient,"search",fail)
    monkeypatch.setattr(socials.MetaClient,"text",lambda *a:pytest.fail("No synthesis without evidence"))
    response=authenticated_client.post(f"/api/v1/workspaces/{workspace}/business-profile/research/profile/social-insights",json={"request_id":str(uuid4()),"urls":[URL],"consent":True})
    assert response.status_code==202
    research.execute_job(response.json()["id"]);research.execute_job(response.json()["id"])
    with SessionLocal() as db:
        data=json.loads(db.get(BrandResearchJob,response.json()["id"]).report_json)["social_research"]
        assert data["status"]=="needs_evidence" and "private-payload" not in json.dumps(data)
    assert calls==[1]
