import io
from uuid import uuid4
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app


def details(**changes):
    return {"name":"Fixture Workshop","industry":"Arts & crafts","description":"Handmade parts for local businesses.",
            "website":"","socials":[],"address":"Kalyani","email":"contact@example.org","phone":"+91 1234567890",**changes}


def profile(client,consent=True,**changes):
    response=client.post("/api/v1/business-profile",json={"details":details(**changes),"consent":consent})
    assert response.status_code==201,response.text
    return response.json()


def test_profile_without_website_skips_without_research_and_persists(authenticated_client):
    client=authenticated_client;item=profile(client,False);base=f'/api/v1/workspaces/{item["workspace_id"]}/business-profile'
    assert not item["onboarding_completed"]
    assert client.get(base+"/research").json()==[]
    result=client.post(base+"/complete",json={"request_id":str(uuid4()),"start_research":False})
    assert result.status_code==200 and result.json()["job"] is None
    with TestClient(app) as reloaded:
        reloaded.headers.update(client.headers)
        saved=reloaded.get(base).json()
        assert saved["onboarding_completed"] and saved["details"]["name"]=="Fixture Workshop"
        assert reloaded.get(base+"/research").json()==[]


def test_start_requires_consent_is_idempotent_and_isolated(authenticated_client):
    client=authenticated_client;item=profile(client,False);base=f'/api/v1/workspaces/{item["workspace_id"]}/business-profile'
    body={"request_id":str(uuid4()),"start_research":True,"use_ai":False}
    assert client.post(base+"/complete",json=body).status_code==422
    item["consent"]=True
    saved=client.post("/api/v1/business-profile",json={"workspace_id":item["workspace_id"],"details":item["details"],"consent":True})
    assert saved.status_code==201
    first=client.post(base+"/complete",json=body)
    second=client.post(base+"/complete",json=body)
    assert first.status_code==200 and first.json()["job"]["id"]==second.json()["job"]["id"]
    assert client.post(base+"/research",json={"request_id":str(uuid4())}).status_code==409
    with TestClient(app) as outsider:
        assert outsider.get(base).status_code==401
        email=str(uuid4())+"@example.org"
        outsider.post("/api/v1/auth/register",json={"email":email,"password":"StrongPassword123"})
        token=outsider.post("/api/v1/auth/login",json={"email":email,"password":"StrongPassword123"}).json()["access_token"]
        outsider.headers.update({"Authorization":"Bearer "+token})
        for suffix in ("","/assets","/research"):
            assert outsider.get(base+suffix).status_code==404
        assert outsider.post(base+"/research",json=body).status_code==404


def test_upload_uses_actual_hash_and_private_download(authenticated_client):
    client=authenticated_client;item=profile(client);base=f'/api/v1/workspaces/{item["workspace_id"]}/business-profile'
    out=io.BytesIO();Image.new("RGB",(30,20),"blue").save(out,format="PNG");payload=out.getvalue()
    def send(digest=None):return client.post(base+"/assets",data={"kind":"logo","consent":"true",**({"sha256":digest} if digest else {})},files={"file":("logo.png",payload,"image/png")})
    assert send("0"*64).status_code==422
    assert client.get(base+"/assets").json()==[]
    first=send();second=send()
    assert first.status_code==201 and second.json()["id"]==first.json()["id"]
    file=client.get(base+"/assets/"+first.json()["id"])
    assert file.content==payload and file.headers["cache-control"]=="private, no-store"
    assert client.post(base+"/assets",data={"consent":"false"},files={"file":("notes.txt",b"notes","text/plain")}).status_code==422


@pytest.mark.parametrize("values",[{"industry":"Other"},{"industry":"Invented"},{"email":"bad email"},
    {"website":"http://example.org"},{"website":"https://facebook.com/example"},
    {"socials":[{"platform":"instagram","url":"https://facebook.com/example"}]}])
def test_profile_rejects_invalid_fields(authenticated_client,values):
    response=authenticated_client.post("/api/v1/business-profile",json={"details":details(**values),"consent":True})
    assert response.status_code==422


def test_edit_only_changes_owner_profile_not_previous_job(authenticated_client):
    client=authenticated_client;item=profile(client);base=f'/api/v1/workspaces/{item["workspace_id"]}/business-profile'
    job=client.post(base+"/research",json={"request_id":str(uuid4()),"use_ai":False}).json()
    saved=client.post("/api/v1/business-profile",json={"workspace_id":item["workspace_id"],"details":details(name="Updated business"),"consent":False})
    assert saved.json()["details"]["name"]=="Updated business"
    assert client.get(base+"/research").json()[0]["input_profile"]["name"]=="Fixture Workshop"
    assert job["state"]=="queued"
