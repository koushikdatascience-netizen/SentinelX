import io
import base64
from uuid import uuid4
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app import workbench
from app.workspace_store import SessionLocal,WorkflowRun
from tests.test_business_onboarding import profile


def payload(workspace,tool="post",**changes):
    return {"workspace_id":workspace,"request_id":str(uuid4()),"tool":tool,"prompt":"Explain custom workshop services clearly.",**changes}


def enabled(monkeypatch):
    monkeypatch.setattr(workbench,"generation_is_live",lambda *a:True)
    monkeypatch.setattr(workbench,"claim_attempt",lambda *a:None)


def post():return {"provenance":"live_meta","model":"offline-test","data":{"title":"Workshop guide","caption":"Discuss your custom requirements with the workshop.","hashtags":["#Workshop"],"image_prompt":"A clear authentic workshop scene with product parts.","video_scenes":["Show a sample wooden part and explain the request process."],"call_to_action":"Send your requirements for review.","assumptions":["Owner to confirm contact details."]}}


def test_post_is_persistent_idempotent_and_includes_visual_briefs(authenticated_client,monkeypatch):
    enabled(monkeypatch);calls=[]
    monkeypatch.setattr(workbench.MetaClient,"text",lambda *a,**k:(calls.append(a) or post()))
    workspace=profile(authenticated_client)["workspace_id"];body=payload(workspace)
    first=authenticated_client.post("/api/v1/workbench",json=body)
    second=authenticated_client.post("/api/v1/workbench",json=body)
    assert first.status_code==201 and second.json()["id"]==first.json()["id"] and len(calls)==1
    assert first.json()["data"]["video_scenes"] and first.json()["data"]["image_prompt"]
    assert authenticated_client.post("/api/v1/workbench",json={**body,"prompt":"A changed request with the same ID"}).status_code==409
    assert authenticated_client.get(f'/api/v1/workbench/{body["request_id"]}/export',params={"workspace_id":workspace,"format":"md"}).status_code==200
    with TestClient(app) as reload:
        reload.headers.update(authenticated_client.headers)
        assert reload.get("/api/v1/workbench",params={"workspace_id":workspace}).json()[0]["id"]==first.json()["id"]


@pytest.mark.parametrize("tool",["competitors","keywords"])
def test_research_is_one_cited_search_without_invented_rankings(authenticated_client,monkeypatch,tool):
    enabled(monkeypatch);calls=[]
    def search(self,query):
        calls.append(query);return {"provenance":"live_meta","model":"offline-test","data":{"summary":"A source-linked candidate.","citations":[{"title":"Source","url":"https://example.org"}],"searched":True}}
    monkeypatch.setattr(workbench.MetaClient,"search",search)
    workspace=profile(authenticated_client)["workspace_id"]
    result=authenticated_client.post("/api/v1/workbench",json=payload(workspace,tool,industry="Manufacturing",location="Kalyani"))
    assert result.status_code==201 and len(calls)==1 and "Kalyani" in calls[0]
    assert result.json()["data"]["citations"] and "verified ranking" in result.json()["limitation"]


def test_failed_paid_request_never_replays_automatically(authenticated_client,monkeypatch):
    enabled(monkeypatch);calls=[]
    def failed(*args,**kwargs):calls.append(1);raise ValueError("provider error")
    monkeypatch.setattr(workbench.MetaClient,"text",failed)
    workspace=profile(authenticated_client)["workspace_id"];body=payload(workspace)
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==502
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==409
    assert calls==[1]


def test_generated_image_retains_live_provenance_on_private_asset(authenticated_client,monkeypatch):
    enabled(monkeypatch)
    out=io.BytesIO();Image.new("RGB",(80,60),"blue").save(out,format="PNG")
    monkeypatch.setattr(workbench.MetaClient,"image",lambda *a,**k:{"provenance":"live_meta","model":"offline-mock-image","data":{"b64_json":base64.b64encode(out.getvalue()).decode(),"format":"png"}})
    workspace=profile(authenticated_client)["workspace_id"]
    response=authenticated_client.post("/api/v1/workbench",json=payload(workspace,"image"))
    assert response.status_code==201 and response.json()["data"]["asset"]["provenance"]=="live_meta"


def test_quota_failure_stops_before_model_request(authenticated_client,monkeypatch):
    enabled(monkeypatch)
    from fastapi import HTTPException
    def denied(*args):raise HTTPException(429,"Campaign generation attempt limit reached")
    monkeypatch.setattr(workbench,"claim_attempt",denied)
    monkeypatch.setattr(workbench.MetaClient,"text",lambda *a,**k:pytest.fail("Quota must block the model request"))
    workspace=profile(authenticated_client)["workspace_id"]
    response=authenticated_client.post("/api/v1/workbench",json=payload(workspace))
    assert response.status_code==429 and "limit reached" in response.json()["detail"]


def test_tools_do_not_fall_back_to_samples_when_paid_flags_off(authenticated_client,monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    workspace=profile(authenticated_client)["workspace_id"]
    assert authenticated_client.post("/api/v1/workbench",json=payload(workspace)).status_code==503


def test_workspace_isolation_for_tools_and_exports(authenticated_client,monkeypatch):
    enabled(monkeypatch);monkeypatch.setattr(workbench.MetaClient,"text",lambda *a,**k:post())
    workspace=profile(authenticated_client)["workspace_id"];body=payload(workspace)
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==201
    with TestClient(app) as outsider:
        email=str(uuid4())+"@example.org";credentials={"email":email,"password":"StrongPassword123"}
        outsider.post("/api/v1/auth/register",json=credentials)
        outsider.headers.update({"Authorization":"Bearer "+outsider.post("/api/v1/auth/login",json=credentials).json()["access_token"]})
        assert outsider.get("/api/v1/workbench",params={"workspace_id":workspace}).status_code==404
        assert outsider.get(f'/api/v1/workbench/{body["request_id"]}/export',params={"workspace_id":workspace}).status_code==404
        assert outsider.post("/api/v1/workbench",json=payload(workspace)).status_code==404


def test_documents_are_chunked_explicitly_and_exportable_without_ai(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client)["workspace_id"]
    monkeypatch.setattr(workbench.MetaClient,"text",lambda *a,**k:pytest.fail("No inference for document parsing"))
    data={"workspace_id":workspace,"request_id":str(uuid4()),"consent":"true","start_page":"1","page_limit":"1"}
    content=("Useful business notes. "*2000).encode()
    result=authenticated_client.post("/api/v1/workbench/documents",data=data,files={"file":("notes.txt",content,"text/plain")})
    assert result.status_code==201 and result.json()["data"]["next_page"]==2
    assert len(result.json()["data"]["pages"][0]["text"])==20000
    assert authenticated_client.get(f'/api/v1/workbench/{result.json()["id"]}/export',params={"workspace_id":workspace,"format":"txt"}).status_code==200
    assert authenticated_client.post("/api/v1/workbench/documents",data={**data,"request_id":str(uuid4()),"consent":"false"},files={"file":("notes.txt",content,"text/plain")}).status_code==422


def test_image_editor_saves_real_resized_bytes_and_uses_no_model(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client)["workspace_id"]
    out=io.BytesIO();Image.new("RGB",(100,60),"red").save(out,format="PNG")
    data={"workspace_id":workspace,"request_id":str(uuid4()),"consent":"true","width":128,"height":96,"output":"webp","fit":"cover","rotation":"90"}
    result=authenticated_client.post("/api/v1/workbench/image-editor",data=data,files={"file":("input.png",out.getvalue(),"image/png")})
    assert result.status_code==201,result.text
    asset=result.json()["data"]["asset"]
    raw=authenticated_client.get(f'/api/v1/workspaces/{workspace}/business-profile/assets/{asset["id"]}')
    with Image.open(io.BytesIO(raw.content)) as image:assert image.size==(128,96) and image.format=="WEBP"


def test_scanned_pdf_pages_are_flagged_and_ranges_validated():
    from pypdf import PdfWriter
    pdf=PdfWriter();pdf.add_blank_page(width=200,height=200);pdf.add_blank_page(width=200,height=200)
    out=io.BytesIO();pdf.write(out)
    result=workbench.extract_document(out.getvalue(),"scan.pdf",1,1)
    assert result["pages"][0]["needs_ocr"] and result["next_page"]==2
    with pytest.raises(ValueError):workbench.extract_document(out.getvalue(),"scan.pdf",3,1)
    with pytest.raises(ValueError):workbench.extract_document(b"binary","file.exe",1,1)
