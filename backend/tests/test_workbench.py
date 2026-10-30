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
    def search(self,query,**options):
        assert options["purpose"]==tool
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


def review_asset(client,workspace):
    out=io.BytesIO();Image.new("RGB",(80,60),"blue").save(out,format="PNG")
    response=client.post(f"/api/v1/workspaces/{workspace}/business-profile/assets",data={"kind":"image","consent":"true"},files={"file":("social-post.png",out.getvalue(),"image/png")})
    assert response.status_code==201
    return response.json()


def review_result():
    return {"provenance":"live_meta","model":"offline-vision","data":{"summary":"The selected product image has room for improvement.","strengths":["The subject is visible."],"improvements":["Use a less distracting background."],"post_guidance":"Leave clear space for a short caption near the subject.","regeneration_prompt":"An original product composition with a clean background and clear lighting.","limitations":["No sales performance was measured."]}}


def test_image_review_is_consented_budget_scoped_persistent_and_links_new_concept(authenticated_client,monkeypatch):
    enabled(monkeypatch);calls=[]
    workspace=profile(authenticated_client)["workspace_id"];asset=review_asset(authenticated_client,workspace)
    def vision(self,body,mime,prompt,schema):
        calls.append(self.run_id);assert self.workspace_id==workspace and self.owner_id and mime=="image/jpeg"
        with Image.open(io.BytesIO(body)) as im:assert im.size==(80,60)
        return review_result()
    monkeypatch.setattr(workbench.MetaClient,"vision",vision)
    monkeypatch.setattr(workbench,"claim_attempt",lambda *a:pytest.fail("Image review must not consume campaign attempts"))
    body=payload(workspace,"image_review",asset_id=asset["id"],consent=True)
    first=authenticated_client.post("/api/v1/workbench",json=body)
    assert first.status_code==201,first.text
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==201 and calls==[body["request_id"]]
    assert first.json()["input_sha256"]==asset["sha256"]
    saved=authenticated_client.get("/api/v1/workbench",params={"workspace_id":workspace}).json()[0]
    assert saved["data"]["regeneration_prompt"]==review_result()["data"]["regeneration_prompt"]
    monkeypatch.setattr(workbench,"claim_attempt",lambda *a:None)
    out=io.BytesIO();Image.new("RGB",(80,60),"red").save(out,format="PNG")
    monkeypatch.setattr(workbench.MetaClient,"image",lambda *a,**k:{"provenance":"live_meta","model":"offline-image","data":{"b64_json":base64.b64encode(out.getvalue()).decode(),"format":"png"}})
    generated=authenticated_client.post("/api/v1/workbench",json=payload(workspace,"image",prompt=saved["data"]["regeneration_prompt"],source_review_id=saved["id"]))
    assert generated.status_code==201
    assert generated.json()["source_asset_id"]==asset["id"] and generated.json()["source_review_id"]==saved["id"]
    assert "not a pixel-preserving edit" in generated.json()["limitation"]


def test_image_review_rejects_missing_consent_foreign_asset_and_corruption_before_inference(authenticated_client,monkeypatch):
    from app.business_store import BrandAsset
    enabled(monkeypatch)
    monkeypatch.setattr(workbench.MetaClient,"vision",lambda *a:pytest.fail("Must stop before paid request"))
    workspace=profile(authenticated_client)["workspace_id"];asset=review_asset(authenticated_client,workspace)
    body=payload(workspace,"image_review",asset_id=asset["id"])
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==422
    other=profile(authenticated_client)["workspace_id"]
    assert authenticated_client.post("/api/v1/workbench",json={**body,"workspace_id":other,"consent":True}).status_code==404
    with SessionLocal() as db:db.get(BrandAsset,asset["id"]).sha256="0"*64;db.commit()
    assert authenticated_client.post("/api/v1/workbench",json={**body,"consent":True}).status_code==422
    assert authenticated_client.post("/api/v1/workbench",json=payload(other,"image",source_review_id=str(uuid4()))).status_code==404


@pytest.mark.parametrize("invalid",[False,True])
def test_failed_or_malformed_image_review_never_replays(authenticated_client,monkeypatch,invalid):
    enabled(monkeypatch);workspace=profile(authenticated_client)["workspace_id"];asset=review_asset(authenticated_client,workspace);calls=[]
    def failed(*args,**kwargs):
        calls.append(1)
        if invalid:return {"provenance":"live_meta","data":{"summary":"Missing fields"}}
        raise ValueError("provider failed")
    monkeypatch.setattr(workbench.MetaClient,"vision",failed)
    body=payload(workspace,"image_review",asset_id=asset["id"],consent=True)
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==502
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==409
    assert calls==[1]


def test_spending_limit_stops_before_http_request(authenticated_client,monkeypatch):
    from tests.test_meta_client import transport
    enabled(monkeypatch)
    for name,value in {"MODEL_API_KEY":"offline-test","INFERENCE_PROVIDER":"meta","SENTINELX_MODE":"live","ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true","META_RUN_BUDGET_CENTS":"0"}.items():monkeypatch.setenv(name,value)
    calls=transport(monkeypatch)
    workspace=profile(authenticated_client)["workspace_id"]
    response=authenticated_client.post("/api/v1/workbench",json=payload(workspace))
    assert response.status_code==429 and "spending limit" in response.json()["detail"] and calls==[]


def test_competitor_research_does_not_consume_campaign_generation_quota(authenticated_client,monkeypatch):
    enabled(monkeypatch)
    from fastapi import HTTPException
    def denied(*args):raise HTTPException(429,"Campaign generation attempt limit reached")
    calls=[]
    monkeypatch.setattr(workbench,"claim_attempt",denied)
    monkeypatch.setattr(workbench.MetaClient,"search",lambda self,query,**options:(calls.append(query) or {
        "provenance":"live_meta","model":"offline-test","data":{"summary":"Candidate evidence.",
        "citations":[{"title":"Source","url":"https://example.org"}],"searched":True}}))
    workspace=profile(authenticated_client)["workspace_id"]
    response=authenticated_client.post("/api/v1/workbench",json=payload(workspace,"competitors",industry="Manufacturing",location="Kalyani"))
    assert response.status_code==201 and len(calls)==1
    assert response.json()["data"]["citations"]


@pytest.mark.parametrize("tool",["post","image_review"])
def test_tools_do_not_fall_back_to_samples_when_paid_flags_off(authenticated_client,monkeypatch,tool):
    monkeypatch.setenv("INFERENCE_PROVIDER","demo")
    workspace=profile(authenticated_client)["workspace_id"]
    assert authenticated_client.post("/api/v1/workbench",json=payload(workspace,tool)).status_code==503


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


@pytest.mark.parametrize("encoding",["utf-8-sig","utf-16","utf-16-be"])
def test_document_text_encodings(encoding):
    text="Workshop order notes: quantities and delivery dates."
    content=text.encode(encoding)
    if encoding=="utf-16-be":content=b"\xfe\xff"+content
    assert workbench.extract_document(content,"notes.txt",1,1)["pages"][0]["text"]==text


def test_document_encoding_and_pdf_errors_are_safe(monkeypatch):
    import pypdf
    with pytest.raises(workbench.DocumentError,match="Text encoding is unsupported"):
        workbench.extract_document(b"private-business-content\xff","notes.txt",1,1)
    def invalid(*args):raise ValueError("private-document-content")
    monkeypatch.setattr(pypdf,"PdfReader",invalid)
    with pytest.raises(workbench.DocumentError,match="could not be opened") as failure:
        workbench.extract_document(b"%PDF-private-business-content","notes.pdf",1,1)
    assert "private-" not in str(failure.value)
    with pytest.raises(workbench.DocumentError,match="starting page"):
        workbench.extract_document(b"notes","notes.txt",0,1)


def test_document_failed_request_is_saved_and_new_explicit_request_can_succeed(authenticated_client,monkeypatch):
    workspace=profile(authenticated_client)["workspace_id"]
    monkeypatch.setattr(workbench.MetaClient,"text",lambda *args:pytest.fail("Local documents must not use inference"))
    body={"workspace_id":workspace,"request_id":str(uuid4()),"consent":"true"}
    invalid=authenticated_client.post("/api/v1/workbench/documents",data=body,files={"file":("notes.pdf",b"not a PDF","application/pdf")})
    assert invalid.status_code==422 and invalid.json()["detail"]=="Invalid PDF"
    assert authenticated_client.post("/api/v1/workbench/documents",data=body,files={"file":("notes.pdf",b"not a PDF","application/pdf")}).status_code==409
    fixed={**body,"request_id":str(uuid4())}
    response=authenticated_client.post("/api/v1/workbench/documents",data=fixed,files={"file":("notes.txt",b"Useful business document notes.","text/plain")})
    assert response.status_code==201,response.text
    assert authenticated_client.post("/api/v1/workbench/documents",data=fixed,files={"file":("notes.txt",b"Useful business document notes.","text/plain")}).json()["id"]==response.json()["id"]
    assert authenticated_client.post("/api/v1/workbench/documents",data=fixed,files={"file":("notes.pdf",b"Useful business document notes.","application/pdf")}).status_code==409
    rows=authenticated_client.get("/api/v1/workbench",params={"workspace_id":workspace}).json()
    assert any(row["status"]=="failed" and row["error"]=="Invalid PDF" for row in rows)
    assert any(row["id"]==response.json()["id"] and row["data"]["pages"][0]["text"]=="Useful business document notes." for row in rows)


def test_pdf_text_layer_is_extracted_persisted_and_exported(authenticated_client):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=300,height=300)
    font=DictionaryObject({NameObject("/Type"):NameObject("/Font"),NameObject("/Subtype"):NameObject("/Type1"),NameObject("/BaseFont"):NameObject("/Helvetica")})
    page[NameObject("/Resources")]=DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b"BT /F1 12 Tf 20 200 Td (Workshop quotation requirements) Tj ET")
    page[NameObject("/Contents")]=writer._add_object(stream)
    out=io.BytesIO();writer.write(out)
    workspace=profile(authenticated_client)["workspace_id"]
    response=authenticated_client.post("/api/v1/workbench/documents",data={"workspace_id":workspace,"request_id":str(uuid4()),"consent":"true"},files={"file":("quotation.pdf",out.getvalue(),"application/pdf")})
    assert response.status_code==201,response.text
    data=response.json()["data"]
    assert data["total_pages"]==1 and "Workshop quotation requirements" in data["pages"][0]["text"]
    assert not data["pages"][0]["needs_ocr"]
    exported=authenticated_client.get(f'/api/v1/workbench/{response.json()["id"]}/export',params={"workspace_id":workspace,"format":"txt"})
    assert exported.status_code==200 and "Workshop quotation requirements" in exported.text


@pytest.mark.parametrize("tool",["competitors","keywords"])
def test_research_preserves_complete_request_and_saved_context_without_cutting_json(authenticated_client,monkeypatch,tool):
    import json
    enabled(monkeypatch);calls=[]
    def search(self,query,**options):
        parsed=json.loads(query);calls.append(parsed)
        assert len(query)<=4000 and parsed["request"].endswith("NEVER INCLUDE RETAIL FURNITURE SHOPS")
        assert parsed["business"]["name"] and parsed["industry"] and parsed["research_date"]
        assert options["purpose"]==tool
        return {"provenance":"live_meta","model":"offline-test","data":{"summary":"Source-backed research notes.","citations":[{"title":"Source","url":"https://example.org"}],"searched":True}}
    monkeypatch.setattr(workbench.MetaClient,"search",search)
    workspace=profile(authenticated_client)["workspace_id"]
    prompt="Find businesses and phrases for trade components. "*25+"NEVER INCLUDE RETAIL FURNITURE SHOPS"
    body=payload(workspace,tool,prompt=prompt)
    first=authenticated_client.post("/api/v1/workbench",json=body)
    assert first.status_code==201,first.text
    assert authenticated_client.post("/api/v1/workbench",json=body).json()["id"]==first.json()["id"]
    assert len(calls)==1


@pytest.mark.parametrize("tool",["competitors","keywords"])
def test_research_budget_failure_is_429_and_persisted_without_retry(authenticated_client,monkeypatch,tool):
    enabled(monkeypatch);calls=[]
    def search(self,*args,**kwargs):calls.append(1);raise ValueError("Meta budget reached for this workspace")
    monkeypatch.setattr(workbench.MetaClient,"search",search)
    workspace=profile(authenticated_client)["workspace_id"];body=payload(workspace,tool)
    first=authenticated_client.post("/api/v1/workbench",json=body)
    assert first.status_code==429 and "spending limit" in first.json()["detail"]
    assert authenticated_client.post("/api/v1/workbench",json=body).status_code==409 and calls==[1]
