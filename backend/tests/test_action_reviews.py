import uuid


def test_competing_review_cannot_overwrite_decision(authenticated_client, monkeypatch):
    from app import workspace_routes
    from app.workspace_store import SessionLocal, ReviewableAction, utcnow
    from sqlalchemy import update

    client = authenticated_client
    wid = client.post("/api/v1/workspaces", json={"name": "Race test"}).json()["id"]
    rid = client.post(f"/api/v1/workspaces/{wid}/runs", json={
        "website": "https://example.com", "goal": "Improve our customer conversion"
    }).json()["id"]
    aid = client.post(f"/api/v1/workspaces/{wid}/runs/{rid}/actions", json={
        "description": "Prepare a consultation booking proposal"
    }).json()["id"]

    def competing_decision():
        # Commit after the route's read but before its conditional write.
        with SessionLocal.begin() as db:
            db.execute(update(ReviewableAction).where(ReviewableAction.id == aid).values(
                state="rejected", reviewed_at=utcnow()))
        return utcnow()

    monkeypatch.setattr(workspace_routes, "utcnow", competing_decision)
    response = client.post(f"/api/v1/workspaces/{wid}/actions/{aid}/review", json={"decision": "approved"})
    assert response.status_code == 409, response.text
    saved = client.get(f"/api/v1/workspaces/{wid}/runs/{rid}/actions").json()
    assert saved[0]["state"] == "rejected"

def test_action_review_is_owner_scoped(authenticated_client):
    client=authenticated_client
    workspace=client.post("/api/v1/workspaces",json={"name":"Owner workspace"})
    assert workspace.status_code==201
    wid=workspace.json()["id"]
    run=client.post(f"/api/v1/workspaces/{wid}/evidence-analysis",json={
        "website":"https://example.com",
        "goal":"Improve customer conversion from our online store",
        "page_title":"Store Home",
        "page_excerpt":"We produce handcrafted cabinetry and wooden furniture with made-to-order consultations."
    })
    assert run.status_code==201,run.text
    rid=run.json()["id"]
    action=client.post(f"/api/v1/workspaces/{wid}/runs/{rid}/actions",json={"description":"Draft a clearer consultation booking button"})
    assert action.status_code==201,action.text
    aid=action.json()["id"]
    assert action.json()["executed"] is False
    approved=client.post(f"/api/v1/workspaces/{wid}/actions/{aid}/review",json={"decision":"approved"})
    assert approved.status_code==200,approved.text
    assert approved.json()["executed"] is False
    assert client.post(f"/api/v1/workspaces/{wid}/actions/{aid}/review",json={"decision":"rejected"}).status_code==409
    assert client.get(f"/api/v1/workspaces/{wid}/runs/{rid}/actions").json()[0]["state"]=="approved"
    foreign_email=str(uuid.uuid4())+"@example.org"
    assert client.post("/api/v1/auth/register",json={"email":foreign_email,"password":"SafePassword123"}).status_code==201
    foreign_token=client.post("/api/v1/auth/login",json={"email":foreign_email,"password":"SafePassword123"}).json()["access_token"]
    headers={"Authorization":"Bearer "+foreign_token}
    assert client.get(f"/api/v1/workspaces/{wid}/runs/{rid}/actions",headers=headers).status_code==404
    assert client.post(f"/api/v1/workspaces/{wid}/actions/{aid}/review",json={"decision":"approved"},headers=headers).status_code==404
