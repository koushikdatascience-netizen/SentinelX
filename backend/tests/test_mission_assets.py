import base64
import json
from io import BytesIO
import pytest
from PIL import Image
from app import meta_client
from app.meta_client import MetaClient
from tests.test_meta_client import live,transport


def png():
    stream=BytesIO();Image.new("RGB",(4,4),"red").save(stream,format="PNG");return stream.getvalue()


@pytest.mark.parametrize("mime,payload,block",[("application/pdf",b"%PDF-1.4\nfixture\n%%EOF","input_file"),
    ("video/mp4",b"\x00\x00\x00\x18ftypisom00000000","input_video")])
def test_inline_responses_media_contract(live,monkeypatch,mime,payload,block):
    calls=transport(monkeypatch,{"id":"r1","object":"response","created_at":1,"model":"muse-spark-1.3",
       "status":"completed","output":[{"id":"m1","type":"message","role":"assistant","status":"completed",
       "content":[{"type":"output_text","text":"Observed media details. Keep clear framing. Improve the opening shot.","annotations":[]}]}],
       "usage":{"input_tokens":12,"output_tokens":20,"total_tokens":32}})
    result=MetaClient(**live,max_tokens=1800).review_media(payload,mime,"Review business media")
    assert result["provenance"]=="live_meta" and len(calls)==1
    body=json.loads(calls[0].content);assert str(calls[0].url)=="https://api.meta.ai/v1/responses"
    assert body["store"] is False and body["max_output_tokens"]==1800
    part=body["input"][0]["content"][1];assert part["type"]==block
    encoded=part.get("file_data") or part["video_url"]
    assert base64.b64decode(encoded.split(",")[1])==payload


def test_media_gates_and_validation_precede_network(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_INFERENCE","false")
    monkeypatch.setattr(meta_client,"OpenAI",lambda **kwargs:pytest.fail("Sample called SDK"))
    assert MetaClient().review_media(b"%PDF-1.4\n%%EOF","application/pdf","Review") ["provenance"]=="sample"
    with pytest.raises(ValueError):MetaClient().review_media(b"not mp4","video/mp4","Review")
    with pytest.raises(ValueError):MetaClient().review_media(b"not pdf","application/pdf","Review")


def mission(client):
    workspace=client.post("/api/v1/workspaces",json={"name":"Report assets"}).json()["id"]
    report=client.post("/api/v1/missions",json={"workspace_id":workspace,"website":"https://example.org",
       "goal":"Assess the website strengths and changes","generation_mode":"sample"}).json()
    return workspace,report["id"]


def test_assets_are_owned_persistent_and_sample_labelled(authenticated_client):
    client=authenticated_client;workspace,report=mission(client);root=f"/api/v1/missions/{report}"
    form={"workspace_id":workspace,"generation_mode":"sample","consent":"true"}
    result=client.post(root+"/media",data=form,files={"file":("chair.png",png(),"image/png")})
    assert result.status_code==201,result.text
    asset=result.json();assert asset["provenance"]=="sample" and asset["input_provenance"]=="user_supplied"
    assert "no image pixels" in asset["text"]
    again=client.post(root+"/media",data=form,files={"file":("chair.png",png(),"image/png")})
    assert again.json()["id"]==asset["id"]
    assert client.post(root+"/media",data={**form,"consent":"false"},files={"file":("chair.png",png(),"image/png")}).status_code==422
    assert client.post(root+"/media",data=form,files={"file":("x.mp4",b"invalid","video/mp4")}).status_code==422
    assert client.post(root+"/media",data={**form,"workspace_id":"not-owned"},files={"file":("chair.png",png(),"image/png")}).status_code==404
    document=client.post(root+"/documents",json={"workspace_id":workspace,"kind":"video_script","generation_mode":"sample"})
    assert document.status_code==201,document.text
    data=document.json();assert "not a generated video" in data["limitation"]
    assert client.post(root+"/documents",json={"workspace_id":workspace,"kind":"video_script","generation_mode":"sample"}).json()["id"]==data["id"]
    rows=client.get(root+"/assets",params={"workspace_id":workspace}).json();assert len(rows)==2
    assert client.get(root+"/assets",params={"workspace_id":"not-owned"}).status_code==404
    html=client.get(root+f'/document/{data["id"]}',params={"workspace_id":workspace,"format":"html"})
    assert html.status_code==200 and "sample" in html.text and "Content-Security-Policy" in html.headers


def test_strength_quotes_are_verified():
    from app.mission import sample_plan,sample_source,validate_plan
    plan=sample_plan();plan["strengths"][0]["quote"]="This is invented supporting evidence."
    with pytest.raises(ValueError):validate_plan(plan,[sample_source()])


def test_document_http_prompt_receives_substantive_saved_twin(authenticated_client,monkeypatch):
    from app.workspace_store import SessionLocal,WorkflowRun
    from tests.test_mission_routes import inputs,live_transport
    from tests.test_meta_client import chat
    client=authenticated_client;body=inputs(client);live_transport(monkeypatch)
    report=client.post("/api/v1/missions",json={**body,"generation_mode":"live","consent_public_fetch":True}).json()
    original="> "+"Provenance disclaimer. "*40+"\n\nObserved turned wooden legs against a plain background.\nUnknown dimensions."
    with SessionLocal.begin() as db:
        row=db.get(WorkflowRun,report["id"]);data=json.loads(row.result_json)
        data["business_context"]=[{"id":"test-twin","kind":"business_twin","provenance":"live_meta","sha256":"fixture","text":original}]
        row.result_json=json.dumps(data)
    calls=transport(monkeypatch,chat("Draft: improve product framing; dimensions remain unknown."))
    result=client.post(f'/api/v1/missions/{report["id"]}/documents',json={"workspace_id":body["workspace_id"],"generation_mode":"live"})
    assert result.status_code==201,result.text
    assert result.json()["provenance"]=="live_meta" and len(calls)==1
    prompt=json.loads(json.loads(calls[0].content)["messages"][1]["content"])
    assert prompt["business_context_unverified"][0]["text"].startswith("Observed turned wooden legs")
    assert "Unknown dimensions." in prompt["business_context_unverified"][0]["text"]
