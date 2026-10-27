"""Owned route coverage for the central Meta client boundary."""
import io
from uuid import uuid4
from unittest.mock import Mock
from PIL import Image
from app import creative_routes, media_routes


def test_image_routes_require_auth(authenticated_client):
    # Fresh unauthenticated client, no valid credentials supplied.
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.post("/api/v1/creative/generate",json={}).status_code==401
        assert client.post("/api/v1/media/image/analyze").status_code==401


def test_scoped_image_routes_and_foreign_owner(authenticated_client,monkeypatch):
    client=authenticated_client
    wid=client.post("/api/v1/workspaces",json={"name":"Image workspace"}).json()["id"]
    rid=client.post(f"/api/v1/workspaces/{wid}/runs",json={"website":"https://example.com","goal":"Improve qualified customer inquiries"}).json()["id"]
    body={"workspace_id":wid,"run_id":rid,"prompt":"Create a blue circle on white"}
    fake=Mock();fake.image.return_value={"provenance":"sample","model":"muse-image-1.0","data":{"b64_json":"fixture"}}
    fake.vision.return_value={"provenance":"sample","model":"muse-spark-1.3","data":"fixture"}
    factory=Mock(return_value=fake)
    monkeypatch.setattr(creative_routes,"MetaClient",factory);monkeypatch.setattr(media_routes,"MetaClient",factory)
    assert client.post("/api/v1/creative/generate",json=body).json()["provenance"]=="sample"
    image=io.BytesIO();Image.new("RGB",(8,8)).save(image,format="PNG")
    path=f"/api/v1/media/image/analyze?workspace_id={wid}&run_id={rid}"
    assert client.post(path,files={"file":("image.png",image.getvalue(),"image/png")}).status_code==200
    factory.reset_mock()
    assert client.post("/api/v1/creative/generate",json={**body,"run_id":str(uuid4())}).status_code==404
    credentials={"email":f"foreign-{uuid4()}@example.org","password":"StrongPassword123"}
    assert client.post("/api/v1/auth/register",json=credentials).status_code==201
    token=client.post("/api/v1/auth/login",json=credentials).json()["access_token"]
    client.headers.update({"Authorization":"Bearer "+token})
    assert client.post("/api/v1/creative/generate",json=body).status_code==404
    assert client.post(path,files={"file":("image.png",image.getvalue(),"image/png")}).status_code==404
    factory.assert_not_called()
