import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app

def test_approval_history_and_approved_only_zip(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Approved Pack"}).json()
    payload={"workspace_id":w["id"],"business_description":"We make bespoke furniture with consultations for new clients.",
             "goal":"Generate meaningful interest in handmade furniture","platforms":["instagram"]}
    response=c.post("/api/v1/campaigns",json=payload)
    assert response.status_code==201,response.text
    campaign=response.json();cid=campaign["id"]
    board=c.get(f"/api/v1/campaigns/{cid}/board",params={"workspace_id":w["id"]})
    assert board.status_code==200,board.text
    approvals=[x for x in board.json() if x["target_kind"]=="campaign_item"]
    assert len(approvals)==7
    approval=approvals[0]
    r=c.post(f"/api/v1/approvals/{approval['id']}/decide",params={"workspace_id":w["id"]},
        json={"decision":"approved","note":"Owner reviewed content"})
    assert r.status_code==200,r.text
    assert r.json()["executed"] is False
    assert c.post(f"/api/v1/approvals/{approval['id']}/decide",params={"workspace_id":w["id"]},
        json={"decision":"rejected"}).status_code==409
    pack=c.get(f"/api/v1/campaigns/{cid}/export",params={"workspace_id":w["id"],"format":"zip"})
    assert pack.status_code==200,pack.text
    with zipfile.ZipFile(io.BytesIO(pack.content)) as z:
        names=z.namelist()
        assert len([x for x in names if x.startswith("posts/")])==1
        assert "README.txt" in names and "evidence.json" in names
        assert "provenance=sample" in z.read("README.txt").decode()
    reopened=c.post(f"/api/v1/approvals/{approval['id']}/decide",
        params={"workspace_id":w["id"]},json={"decision":"reopen","note":"Needs further revision"})
    assert reopened.status_code==200
    board2=c.get(f"/api/v1/campaigns/{cid}/board",params={"workspace_id":w["id"]})
    entry=next(x for x in board2.json() if x["id"]==approval["id"])
    assert entry["state"]=="proposed"
    assert [e["decision"] for e in entry["events"]]==["approved","reopen"]
    p2=c.get(f"/api/v1/campaigns/{cid}/export",params={"workspace_id":w["id"]})
    with zipfile.ZipFile(io.BytesIO(p2.content)) as z:
        assert not any(n.startswith("posts/") for n in z.namelist())
    assert c.get(f"/api/v1/campaigns/{cid}/export",params={"workspace_id":"different"}).status_code==404

def test_board_requires_authentication():
    assert TestClient(app).get("/api/v1/campaigns/missing/board",params={"workspace_id":"none"}).status_code==401
