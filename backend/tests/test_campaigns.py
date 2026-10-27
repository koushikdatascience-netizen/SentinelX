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
    cid=body["id"];iid=body["items"][0]["id"]
    changed=c.patch(f"/api/v1/campaigns/{cid}/items/{iid}",params={"workspace_id":wid},
                    json={"caption":"An improved and more useful furniture campaign sample caption."})
    assert changed.status_code==200,changed.text
    assert changed.json()["provenance"]=="user_edited"
    got=c.get(f"/api/v1/campaigns/{cid}",params={"workspace_id":wid})
    assert got.status_code==200
    assert got.json()["items"][0]["provenance"]=="user_edited"
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
