import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import SessionLocal,WorkflowRun
from app.data_hub import parse_isolated
from tests.test_mission_routes import inputs
from tests.test_data_parser import pdf_bytes


def test_multi_file_intake_preview_quality_export_and_deletion(authenticated_client):
    client=authenticated_client;wid=inputs(client)["workspace_id"];scope="?workspace_id="+wid
    files=[("files",("sales.csv",b"product,amount\nLeg,10.25\nPanel,20\nLeg,10.25\n","text/csv")),
        ("files",("handbook.pdf",pdf_bytes(),"application/pdf"))]
    uploaded=client.post("/api/v1/data-hub",data={"workspace_id":wid,"consent":"true"},files=files)
    assert uploaded.status_code==201,uploaded.text
    assert len(uploaded.json()["datasets"])==2 and not uploaded.json()["sent_to_ai"]
    dataset=uploaded.json()["datasets"][0];dataset_id=dataset["id"]
    preview=client.get("/api/v1/data-hub/"+dataset_id+scope).json()
    assert preview["analysis"]["columns"][1]["sum"]=="40.50" and preview["analysis"]["duplicate_rows"]==1
    duplicate=client.post("/api/v1/data-hub",data={"workspace_id":wid,"consent":"true"},files=files).json()
    assert duplicate["datasets"][0]["id"]==dataset_id and duplicate["datasets"][0]["version"]==1
    answer=client.post("/api/v1/intelligence/ask"+scope,json={"question":"What is the total sales amount?","dataset_ids":[dataset_id]}).json()
    assert answer["model_calls"]==0 and "40.50" in answer["evidence"][0]["quote"]
    original=client.get("/api/v1/data-hub/"+dataset_id+"/download"+scope)
    assert original.content==files[0][1][1] and original.headers["x-content-type-options"]=="nosniff"
    assert client.delete("/api/v1/data-hub/"+dataset_id+scope).json()["original_and_analysis_removed"]
    assert client.get("/api/v1/data-hub/"+dataset_id+scope).status_code==404
    with SessionLocal() as db:assert json.loads(db.get(WorkflowRun,answer["id"]).result_json)["redacted"]


def test_formula_text_safe_export_versions_and_actual_tenant_isolation(authenticated_client):
    client=authenticated_client;wid=inputs(client)["workspace_id"];scope="?workspace_id="+wid
    def upload(content):return client.post("/api/v1/data-hub",data={"workspace_id":wid,"consent":"true"},files={"files":("catalog.csv",content,"text/csv")})
    first=upload(b'name,value\n=HYPERLINK("bad"),5\n').json()["datasets"][0]
    second=upload(b'name,value\nPart,6\n').json()["datasets"][0]
    assert second["version"]==2 and second["id"]!=first["id"]
    safe=client.get("/api/v1/data-hub/"+first["id"]+"/download"+scope+"&format=safe_csv")
    assert "'=HYPERLINK" in safe.content.decode("utf-8-sig")
    other=TestClient(app);account={"email":"outsider-"+str(uuid4())+"@example.org","password":"StrongPassword123"}
    other.post("/api/v1/auth/register",json=account);token=other.post("/api/v1/auth/login",json=account).json()["access_token"]
    other.headers["Authorization"]="Bearer "+token
    own=other.post("/api/v1/workspaces",json={"name":"Other tenant"}).json()["id"]
    for target in (wid,own):
        assert other.get("/api/v1/data-hub/"+first["id"]+"?workspace_id="+target).status_code==404
        assert other.delete("/api/v1/data-hub/"+first["id"]+"?workspace_id="+target).status_code==404
        assert other.post("/api/v1/intelligence/ask?workspace_id="+target,json={"question":"Read their data","dataset_ids":[first["id"]]}).status_code==404


def test_invalid_batches_and_missing_consent_do_not_store_private_files(authenticated_client):
    client=authenticated_client;wid=inputs(client)["workspace_id"]
    assert client.post("/api/v1/data-hub",data={"workspace_id":wid},files={"files":("note.txt",b"private notes","text/plain")}).status_code==422
    rejected=client.post("/api/v1/data-hub",data={"workspace_id":wid,"consent":"true"},files={"files":("bad.pdf",b"malicious","application/pdf")})
    assert rejected.status_code==201 and rejected.json()["datasets"]==[] and rejected.json()["errors"]
    assert client.get("/api/v1/data-hub?workspace_id="+wid).json()==[]
    oversized=client.post("/api/v1/data-hub",data={"workspace_id":wid,"consent":"true"},files={"files":("huge.txt",b"x"*6_500_001,"text/plain")})
    assert oversized.status_code in (400,413)


def test_parser_runs_real_subprocess_without_model_credentials(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY","must-not-be-in-parser")
    result=parse_isolated(b"item,units\nLeg,4\nPanel,2\n","csv")
    assert result["columns"][1]["sum"]=="6"
