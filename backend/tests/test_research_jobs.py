import json
from app.workspace_store import SessionLocal
from app.intelligence_store import ResearchJob,BusinessFact
from app.research_jobs import materialize_facts,run_job
from app.site_research import analyze_page
from tests.test_site_research import fake_site,response,HOME
from tests.test_intelligence_routes import begin


def test_refresh_retains_review_history_but_invalidates_changed_evidence(authenticated_client,monkeypatch):
    client=authenticated_client;fake_site(monkeypatch);wid,jid,_=begin(client);run_job(jid,pause=lambda _:None)
    facts=client.get("/api/v1/intelligence/twin?workspace_id="+wid).json()["facts"]
    social=next(item for item in facts if item["kind"]=="social_profile")
    client.post("/api/v1/intelligence/facts/"+social["id"]+"/review?workspace_id="+wid,json={"decision":"owner_confirmed","note":"Reviewed original identity"})
    with SessionLocal.begin() as db:
        job=db.get(ResearchJob,jid);data=json.loads(job.payload_json);materialize_facts(db,job,data)
    with SessionLocal() as db:assert db.get(BusinessFact,social["id"]).verification=="owner_confirmed"
    with SessionLocal.begin() as db:
        job=db.get(ResearchJob,jid)
        page=analyze_page(response("https://example.com/",HOME+"<p>Changed source</p>"),"business")
        materialize_facts(db,job,{"pages":[page]})
    with SessionLocal() as db:
        row=db.get(BusinessFact,social["id"])
        assert row.verification=="source_observed" and json.loads(row.evidence_json)["reviews"][0]["note"]=="Reviewed original identity"
