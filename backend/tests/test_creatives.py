import io
import zipfile
from app.creatives import sample_gradient
from app.image_scoring import measure_image

def test_sample_gradients_are_real_images():
    sample=sample_gradient("fixed-seed")
    assert measure_image(sample)["format"]=="PNG"
    assert sample==sample_gradient("fixed-seed")

def test_owner_can_create_select_and_approve_creative(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Art Workshop"}).json()
    camp=c.post("/api/v1/campaigns",json={"workspace_id":w["id"],
      "business_description":"We create handmade wooden chairs and cabinets for homes.",
      "goal":"Increase customer inquiries for custom wood furniture",
      "platforms":["instagram"]})
    assert camp.status_code==201,camp.text
    cid=camp.json()["id"];iid=camp.json()["items"][0]["id"]
    route=f"/api/v1/campaigns/{cid}/items/{iid}/creatives"
    result=c.post(route,params={"workspace_id":w["id"]},json={"variants":2})
    assert result.status_code==201,result.text
    assert result.json()["created_count"]==2
    variants=result.json()["variants"]
    assert all(v["provenance"]=="sample" for v in variants)
    assert all(v["scores"]["final_score"] is None for v in variants)
    image=c.get(f"{route}/{variants[0]['id']}/image",params={"workspace_id":w["id"]})
    assert image.status_code==200 and image.headers["content-type"]=="image/png"
    select=c.post(f"{route}/{variants[0]['id']}/select",params={"workspace_id":w["id"]})
    assert select.status_code==200 and select.json()["selected"] is True
    assert c.delete(f"{route}/{variants[0]['id']}",params={"workspace_id":w["id"]}).status_code==409
    board=c.get(f"/api/v1/campaigns/{cid}/board",params={"workspace_id":w["id"]})
    assert board.status_code==200,board.text
    creative_review=next(x for x in board.json() if x["target_kind"]=="creative" and x["target_id"]==variants[0]["id"])
    approved=c.post(f"/api/v1/approvals/{creative_review['id']}/decide",
        params={"workspace_id":w["id"]},json={"decision":"approved"})
    assert approved.status_code==200,approved.text
    pack=c.get(f"/api/v1/campaigns/{cid}/export",params={"workspace_id":w["id"]})
    with zipfile.ZipFile(io.BytesIO(pack.content)) as z:
        assert sum(x.startswith("creatives/") for x in z.namelist())==1
    assert c.delete(f"{route}/{variants[1]['id']}",params={"workspace_id":"unrelated"}).status_code==404
