import io
import uuid
from PIL import Image
from fastapi.testclient import TestClient
from app.image_scoring import measure_image
from app.main import app

def png(color=(170,130,80),size=(320,240)):
    buffer=io.BytesIO()
    Image.new("RGB",size,color).save(buffer,format="PNG")
    return buffer.getvalue()

def test_measurements_are_real_local_metrics():
    data=measure_image(png())
    assert data["width"]==320 and data["height"]==240
    assert data["provenance"]=="user_supplied"
    assert len(data["dominant_colors"])>=1
    assert data["brightness"]>0

def test_bad_image_rejected():
    import pytest
    with pytest.raises(ValueError):measure_image(b"not an image")

def test_scoring_isolated_and_does_not_fabricate_meta(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Photo Studio"})
    assert w.status_code==201
    workspace=w.json()["id"]
    resp=c.post("/api/v1/images/score",data={"workspace_id":workspace,"business_context":"Custom chairs"},
                files={"file":("chair.png",png(),"image/png")})
    assert resp.status_code==201,resp.text
    payload=resp.json()
    assert payload["result"]["provenance"]=="user_supplied"
    assert payload["result"]["final_score"] is None
    assert payload["result"]["segmentation"]=="not_run"
    iid=payload["id"]
    assert c.get(f"/api/v1/images/{iid}",params={"workspace_id":workspace}).status_code==200
    assert c.delete(f"/api/v1/images/{iid}",params={"workspace_id":workspace}).status_code==204
    assert c.get(f"/api/v1/images/{iid}",params={"workspace_id":workspace}).status_code==404

def test_anonymous_image_score_rejected():
    resp=TestClient(app).post("/api/v1/images/score",data={"workspace_id":str(uuid.uuid4())},
                 files={"file":("chair.png",png(),"image/png")})
    assert resp.status_code==401
