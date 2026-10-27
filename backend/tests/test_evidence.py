from app.evidence import Recommendation, assess

def test_requires_review():
    item = Recommendation(claim='Website appears to lack a clear call to action', action='Review landing page copy with the business owner')
    result = assess(item)
    assert result['status'] == 'unverified'
    assert result['execution_performed'] is False
    assert result['approval_required'] is True


def test_client_cannot_self_attest_independent_collection(authenticated_client):
    response = authenticated_client.post("/api/v1/evidence/assess", json={
        "claim": "Our website has the best furniture prices",
        "action": "Review the pricing claim with the business owner",
        "evidence": [{"url": "https://example.com", "excerpt": "Owner-provided product description", "collected": True}],
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unverified"
    assert response.json()["source_type"] == "user_supplied_unverified"
    assert response.json()["usable_sources"] == []
