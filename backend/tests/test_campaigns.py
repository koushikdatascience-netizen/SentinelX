import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.campaign import unsupported_claims

def payload(wid):
    return {"workspace_id":wid,"business_description":"We make custom wooden furniture and cabinetry. Buyers can request a consultation.",
            "goal":"Increase qualified inquiries for custom furniture","language":"en",
            "platforms":["instagram","facebook"]}

def test_demo_campaign_seven_days_isolation_and_edits(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Furniture business"})
    assert w.status_code==201
    wid=w.json()["id"]
    resp=c.post("/api/v1/campaigns",json=payload(wid))
    assert resp.status_code==201,resp.text
    body=resp.json()
    assert body["provenance"]=="sample"
    assert len(body["items"])==7
    assert all(x["state"]=="proposed" for x in body["items"])
    assert all(x["image_prompt"] and x["creative_brief"] and x["hashtags"] and x["cta"] for x in body["items"])
    cid=body["id"];iid=body["items"][0]["id"]
    changed=c.patch(f"/api/v1/campaigns/{cid}/items/{iid}",params={"workspace_id":wid},
                    json={"caption":"An improved and more useful furniture campaign sample caption.",
                          "hashtags":["#CustomFurniture","#MadeToOrder"],
                          "image_prompt":"Use an owner-approved furniture image in a bright, natural workshop setting.",
                          "video_script":"Scene 1: show the owner-provided cabinet image. Scene 2: invite questions."})
    assert changed.status_code==200,changed.text
    assert changed.json()["provenance"]=="user_supplied"
    got=c.get(f"/api/v1/campaigns/{cid}",params={"workspace_id":wid})
    assert got.status_code==200
    assert got.json()["items"][0]["provenance"]=="user_supplied"
    assert got.json()["items"][0]["hashtags"]==["#CustomFurniture","#MadeToOrder"]
    assert got.json()["items"][0]["image_prompt"].startswith("Use an owner-approved")
    assert got.json()["items"][0]["video_script"].startswith("Scene 1")
    assert c.get("/api/v1/campaigns",params={"workspace_id":wid}).json()[0]["id"]==cid
    assert c.get(f"/api/v1/campaigns/{cid}",params={"workspace_id":"invalid"}).status_code==404

def test_public_campaign_access_rejected():
    c=TestClient(app)
    assert c.get("/api/v1/campaigns",params={"workspace_id":"abc"}).status_code==401

def test_nonnative_sample_languages(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Language Tests"}).json()
    for lang in ("bn","hi"):
        p=payload(w["id"]);p["language"]=lang
        response=c.post("/api/v1/campaigns",json=p)
        assert response.status_code==201,response.text
        assert response.json()["language"]==lang
        assert response.json()["items"][0]["caption"]

def test_unsupported_sales_claim_flagging():
    assert unsupported_claims("Guaranteed increase of 30% revenue")

def test_supported_platforms_and_persisted_campaign_fields(authenticated_client):
    c=authenticated_client
    workspace=c.post("/api/v1/workspaces",json={"name":"Multi-platform business"}).json()["id"]
    platforms=["instagram","facebook","whatsapp","linkedin","x","google_business_profile","youtube"]
    response=c.post("/api/v1/campaigns",json={**payload(workspace),"platforms":platforms})
    assert response.status_code==201,response.text
    assert {item["platform"] for item in response.json()["items"]}==set(platforms)
    assert all(item["image_prompt"] and item["video_script"] is None for item in response.json()["items"])
    blogger=c.post("/api/v1/campaigns",json={**payload(workspace),"platforms":["blogger"]})
    assert blogger.status_code==201 and {item["platform"] for item in blogger.json()["items"]}=={"blogger"}
    rejected=c.post("/api/v1/campaigns",json={**payload(workspace),"platforms":platforms+["blogger"]})
    assert rejected.status_code==422

def test_reel_requires_video_script():
    from pydantic import ValidationError
    from app.campaign import DayPlan
    base={"day":1,"platform":"instagram","post_type":"Product Reel","caption":"Show the product design and options.",
          "hashtags":["#woodwork"],"cta":"Ask us about custom options.","creative_brief":"Use an owner-approved product photo in natural light.",
          "image_prompt":"Create a natural-light image using only owner-provided product details.","evidence_ids":[]}
    with pytest.raises(ValidationError):DayPlan.model_validate(base)
    assert DayPlan.model_validate({**base,"video_script":"Scene 1: show the supplied product photo; Scene 2: invite questions."}).video_script

def test_requested_live_never_substitutes_samples(authenticated_client,monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    c=authenticated_client
    wid=c.post("/api/v1/workspaces",json={"name":"Live request"}).json()["id"]
    request={**payload(wid),"generation_mode":"live"}
    response=c.post("/api/v1/campaigns",json=request)
    assert response.status_code==503
    assert "No sample was substituted" in response.json()["detail"]
    assert c.get("/api/v1/campaigns",params={"workspace_id":wid}).json()==[]
    assert c.get("/api/v1/campaigns/runtime").json()["mode"]=="unavailable"

def test_browser_can_preflight_authenticated_edits():
    response=TestClient(app).options("/api/v1/landing/test",headers={
        "Origin":"http://localhost:3000","Access-Control-Request-Method":"PATCH",
        "Access-Control-Request-Headers":"authorization,content-type"})
    assert response.status_code==200
    assert "PATCH" in response.headers["access-control-allow-methods"]
