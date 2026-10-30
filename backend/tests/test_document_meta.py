import base64
import io
import json
from uuid import uuid4
import httpx
import pytest
from openai import OpenAI as SDK
from pypdf import PdfReader,PdfWriter
from app import meta_client
from app.workspace_store import SessionLocal,WorkflowRun
from tests.test_business_onboarding import profile
from tests.test_business_visuals import enable
from tests.test_engine_inputs import grounded


def pdf(count=6):
    writer=PdfWriter()
    for _ in range(count):writer.add_blank_page(width=200,height=200)
    out=io.BytesIO();writer.write(out);return out.getvalue()


def setup(client,monkeypatch,handler):
    workspace=profile(client)["workspace_id"];enable(monkeypatch)
    def factory(**kwargs):
        assert kwargs["max_retries"]==0
        return SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(meta_client,"OpenAI",factory)
    return workspace


def reply(data):
    response=grounded();response["output"]=response["output"][1:]
    response["output"][0]["content"][0].update(text=json.dumps(data),annotations=[])
    return httpx.Response(200,json=response)


def body(workspace):return {"workspace_id":workspace,"request_id":str(uuid4()),"consent":"true","use_meta":"true","meta_consent":"true","page_limit":"25"}


def test_meta_scanned_pages_are_subsetted_budgeted_and_persisted_without_duplicate_calls(authenticated_client,monkeypatch):
    calls=[]
    def handle(request):
        payload=json.loads(request.content);calls.append(payload)
        assert request.url.path.endswith("/responses") and payload["store"] is False
        content=payload["input"][0]["content"][1]["file_data"]
        pages=PdfReader(io.BytesIO(base64.b64decode(content.split(",",1)[1]))).pages
        assert len(pages)==5
        return reply({"pages":[{"page":i,"text":f"Transcribed workshop page {i}","readable":True} for i in range(1,6)]})
    workspace=setup(authenticated_client,monkeypatch,handle);data=body(workspace)
    files={"file":("scan.pdf",pdf(),"application/pdf")}
    result=authenticated_client.post("/api/v1/workbench/documents",data=data,files=files)
    assert result.status_code==201,result.text
    assert result.json()["provenance"]=="live_meta" and result.json()["model"]=="muse-spark-1.3"
    assert result.json()["data"]["next_page"]==6
    assert all(page["provenance"]=="live_meta" and page["extraction_method"]=="meta_pdf" for page in result.json()["data"]["pages"])
    assert authenticated_client.post("/api/v1/workbench/documents",data=data,files=files).json()["id"]==result.json()["id"]
    saved=authenticated_client.get("/api/v1/workbench",params={"workspace_id":workspace}).json()[0]
    assert saved["data"]==result.json()["data"] and len(calls)==1


@pytest.mark.parametrize("failure",["missing","duplicate","malformed","http"])
def test_failed_meta_documents_keep_local_evidence_and_never_auto_retry(authenticated_client,monkeypatch,failure):
    calls=[]
    def handle(request):
        calls.append(1)
        if failure=="http":return httpx.Response(500,json={"error":{"message":"private-provider-payload"}})
        if failure=="malformed":return reply({"unknown":"private-provider-payload"})
        pages=[{"page":1,"text":"Transcribed text","readable":True}]
        if failure=="missing":pages=[]
        if failure=="duplicate":pages=pages*2
        return reply({"pages":pages})
    workspace=setup(authenticated_client,monkeypatch,handle);data=body(workspace);data["page_limit"]="1"
    files={"file":("scan.pdf",pdf(1),"application/pdf")}
    response=authenticated_client.post("/api/v1/workbench/documents",data=data,files=files)
    assert response.status_code==502 and "private-provider" not in response.text
    assert authenticated_client.post("/api/v1/workbench/documents",data=data,files=files).status_code==409
    with SessionLocal() as db:
        row=db.get(WorkflowRun,data["request_id"]);result=json.loads(row.result_json)
        assert row.status=="failed" and result["data"]["pages"][0]["needs_ocr"]
        assert result["provenance"]=="user_supplied"
    assert calls==[1]


def test_meta_document_consent_owner_flags_and_budget_prevent_http(authenticated_client,monkeypatch):
    workspace=setup(authenticated_client,monkeypatch,lambda req:pytest.fail("No HTTP request allowed"))
    data=body(workspace);files={"file":("scan.pdf",pdf(1),"application/pdf")}
    assert authenticated_client.post("/api/v1/workbench/documents",data={**data,"meta_consent":"false"},files=files).status_code==422
    assert authenticated_client.post("/api/v1/workbench/documents",data={**data,"workspace_id":"foreign"},files=files).status_code==404
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    assert authenticated_client.post("/api/v1/workbench/documents",data=data,files=files).status_code==503
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","true");monkeypatch.setenv("META_RUN_BUDGET_CENTS","0")
    assert authenticated_client.post("/api/v1/workbench/documents",data={**data,"request_id":str(uuid4())},files=files).status_code==429


def test_meta_mapping_uses_original_page_numbers_and_preserves_local_text(monkeypatch):
    from app.document_meta import extract_scans
    def review(self,content,mime,prompt):
        assert len(PdfReader(io.BytesIO(content)).pages)==1 and "[6]" in prompt
        return {"provenance":"live_meta","model":"muse-spark-1.3","data":json.dumps({"pages":[{"page":6,"text":"Final scanned page text","readable":True}]})}
    monkeypatch.setattr(meta_client.MetaClient,"review_media",review)
    data={"pages":[{"page":5,"text":"Existing local text","needs_ocr":False,"provenance":"user_supplied"},{"page":6,"text":"","needs_ocr":True,"provenance":"user_supplied"}]}
    extract_scans(pdf(),data,"owner","workspace","run")
    assert data["pages"][0]["text"]=="Existing local text" and data["pages"][0]["provenance"]=="user_supplied"
    assert data["pages"][1]["text"]=="Final scanned page text" and data["pages"][1]["provenance"]=="live_meta"
