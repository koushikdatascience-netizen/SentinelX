from fastapi.testclient import TestClient
from app.main import app
from app.landing import LandingSpec, sample_landing, render_landing

def test_xss_escaped_and_self_contained():
    raw=sample_landing("Custom furniture","Receive useful inquiries")
    raw["business_name"]="<script>alert(1)</script>"
    raw["headline"]="Safe offers for <img src=x onerror=alert(1)> projects"
    spec=LandingSpec.model_validate(raw)
    html=render_landing(spec,"safe-slug","sample")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x" not in html
    assert "Sample / draft page" in html
    assert "https://fonts." not in html

def test_landing_can_preview_export_and_record_consent(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Landing Workshop"}).json()
    campaign=c.post("/api/v1/campaigns",json={
      "workspace_id":w["id"],"business_description":"We build custom wooden cabinets and work with residential customers.",
      "goal":"Improve the number of good consultation inquiries","language":"en","platforms":["instagram"]})
    assert campaign.status_code==201,campaign.text
    page=c.post("/api/v1/landing/generate",json={
      "workspace_id":w["id"],"campaign_id":campaign.json()["id"],"business_name":"Furniture Studio","theme":"warm"})
    assert page.status_code==201,page.text
    p=page.json();pid=p["id"];slug=p["slug"]
    assert p["published"] is False and p["leads_count"]==0
    pre=c.get(f"/api/v1/landing/{pid}/preview",params={"workspace_id":w["id"]})
    assert pre.status_code==200 and "Content-Security-Policy" in pre.headers
    exported=c.get(f"/api/v1/landing/{pid}/export",params={"workspace_id":w["id"]})
    assert exported.status_code==200 and "<!doctype html>" in exported.text
    assert c.get(f"/p/{slug}").status_code==404
    published=c.patch(f"/api/v1/landing/{pid}",params={"workspace_id":w["id"]},
             json={"published":True})
    assert published.status_code==200
    assert c.get(f"/p/{slug}").status_code==200
    assert c.post(f"/p/{slug}/lead",data={"name":"A Customer","phone":"1234567890","message":"Need a cabinet","consent":""}).status_code==422
    for i in range(4):
        lead=c.post(f"/p/{slug}/lead",data={"name":"A Customer","phone":"1234567890","message":f"Need cabinet {i}","consent":"yes"})
        assert lead.status_code==200,lead.text
    assert c.post(f"/p/{slug}/lead",data={"name":"A Customer","phone":"1234567890","message":"Need cabinet again","consent":"yes"}).status_code==429
    leads=c.get(f"/api/v1/landing/{pid}/leads",params={"workspace_id":w["id"]})
    assert leads.status_code==200 and len(leads.json())==4
    assert c.delete(f"/api/v1/landing/{pid}/leads/{leads.json()[0]['id']}",
        params={"workspace_id":w["id"]}).status_code==204
    assert c.patch(f"/api/v1/landing/{pid}",params={"workspace_id":w["id"]},
        json={"published":False}).status_code==200
    assert c.get(f"/p/{slug}").status_code==404

def test_other_owner_cannot_list_pages(authenticated_client):
    c=authenticated_client
    assert c.get("/api/v1/landing",params={"workspace_id":"not-mine"}).status_code==404
    assert TestClient(app).get("/api/v1/landing",params={"workspace_id":"any"}).status_code==401
