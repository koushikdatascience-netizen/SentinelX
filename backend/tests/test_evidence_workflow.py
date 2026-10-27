def test_owner_supplied_evidence_is_persisted(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Demo Shop"});assert w.status_code==201,w.text
    wid=w.json()["id"]
    result=c.post(f"/api/v1/workspaces/{wid}/evidence-analysis",json={
        "website":"https://example.com",
        "goal":"Improve qualified customer inquiries without fabricating evidence",
        "page_title":"Demo Retail Store",
        "page_excerpt":"We sell custom handmade wooden furniture and offer consultations for residential projects."
    })
    assert result.status_code==201,result.text
    body=result.json()
    assert body["result"]["mode"]=="owner_supplied_evidence"
    assert body["result"]["external_actions_performed"]==0
    assert body["result"]["evidence"][0]["fetched_by_server"] is False
    saved=c.get(f"/api/v1/workspaces/{wid}/runs/{body['id']}")
    assert saved.status_code==200
    assert saved.json()["result"]["plan"]["actions"][0]["approval_required"] is True
