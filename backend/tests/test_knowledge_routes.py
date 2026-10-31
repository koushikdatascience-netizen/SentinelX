import io
import json
from uuid import uuid4
import httpx
import pytest
from openai import OpenAI as SDK
from pypdf import PdfWriter
from app import meta_client
from app.business_store import BrandAsset
from app.workspace_store import SessionLocal
from tests.test_business_onboarding import profile
from tests.test_business_visuals import enable
from tests.test_engine_inputs import grounded
from tests.test_business_data import CSV


def upload(client,wid,filename,payload,mime="text/plain"):
    response=client.post(f"/api/v1/workspaces/{wid}/business-profile/assets",data={"kind":"knowledge","consent":"true"},files={"file":(filename,payload,mime)})
    assert response.status_code==201,response.text
    return response.json()


def test_knowledge_upload_and_data_analysis_are_private_and_make_no_model_calls(authenticated_client,monkeypatch):
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:pytest.fail("Uploads/calculations must be local"))
    wid=profile(authenticated_client)["workspace_id"]
    asset=upload(authenticated_client,wid,"sales.csv",CSV)
    assert asset["metadata"]["dataset_profile"]["rows_analyzed"]==3
    path=f"/api/v1/workspaces/{wid}/knowledge/{asset['id']}/analyze"
    result=authenticated_client.post(path,json={"metric":"Sales","group_by":"Region"})
    assert result.status_code==200 and result.json()["results"][0]["value"]=="180.40"
    assert authenticated_client.post(path.replace(wid,"foreign"),json={"metric":"Sales"}).status_code==404
    saved=authenticated_client.get(f"/api/v1/workspaces/{wid}/business-profile/assets").json()
    assert saved[0]["metadata"]["dataset_profile"]==asset["metadata"]["dataset_profile"]


def test_meta_pdf_knowledge_is_cached_and_not_paid_for_again(authenticated_client,monkeypatch):
    wid=profile(authenticated_client)["workspace_id"];enable(monkeypatch);calls=[]
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.add_blank_page(width=100,height=100)
    out=io.BytesIO();writer.write(out);asset=upload(authenticated_client,wid,"scan.pdf",out.getvalue(),"application/pdf")
    def handle(request):
        calls.append(request);payload=grounded();payload["output"]=payload["output"][1:]
        payload["output"][0]["content"][0].update(text=json.dumps({"pages":[{"page":1,"text":"Owner sales report page one.","readable":True},{"page":2,"text":"Owner sales report page two.","readable":True}]}),annotations=[])
        return httpx.Response(200,json=payload)
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:SDK(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(handle))))
    path=f"/api/v1/workspaces/{wid}/knowledge/{asset['id']}/read";body={"request_id":str(uuid4()),"consent":True,"page_limit":2}
    assert authenticated_client.post(path,json={**body,"consent":False}).status_code==422
    first=authenticated_client.post(path,json=body);assert first.status_code==200,first.text
    assert authenticated_client.post(path,json=body).json()["id"]==first.json()["id"]
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    second=authenticated_client.post(path,json={**body,"request_id":str(uuid4())})
    assert second.status_code==200 and second.json()["provenance"]=="live_meta" and len(calls)==1
    saved=authenticated_client.get(f"/api/v1/workspaces/{wid}/business-profile/assets").json()[0]
    assert "Owner sales report page two" in saved["metadata"]["knowledge_text"]
    with SessionLocal() as db:db.get(BrandAsset,asset["id"]).content=b"tampered";db.commit()
    assert authenticated_client.post(path,json={**body,"request_id":str(uuid4())}).status_code==422 and len(calls)==1
