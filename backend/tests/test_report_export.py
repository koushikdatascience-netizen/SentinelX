def test_report_download_is_owner_scoped(authenticated_client):
    c=authenticated_client
    w=c.post("/api/v1/workspaces",json={"name":"Furniture Demo"})
    assert w.status_code==201
    wid=w.json()["id"]
    body={"website":"https://example.com","goal":"Improve online furniture inquiries","page_title":"Custom Joinery","page_excerpt":"Custom cabinetry and woodwork with consultations available by appointment."}
    r=c.post(f"/api/v1/workspaces/{wid}/evidence-analysis",json=body)
    assert r.status_code==201,r.text
    rid=r.json()["id"]
    report=c.get(f"/api/v1/workspaces/{wid}/runs/{rid}/report")
    assert report.status_code==200
    assert "text/markdown" in report.headers["content-type"]
    assert "user_supplied_unverified" in report.text
    assert "no external execution" not in report.text.lower() or "No action decisions" in report.text
    assert c.get(f"/api/v1/workspaces/{wid}/runs/missing/report").status_code==404
    assert c.get(f"/api/v1/workspaces/{wid}/runs/{rid}/report",headers={"Authorization":"Bearer invalid"}).status_code==401
