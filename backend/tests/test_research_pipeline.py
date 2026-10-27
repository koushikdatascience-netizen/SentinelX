from app import research_pipeline

def test_pipeline_preserves_source(monkeypatch):
    monkeypatch.setattr(research_pipeline, "snapshot", lambda url: {
        "evidence_source": url, "title": "Sample bakery", "text": "Bakery sells cakes and biscuits"
    })
    result=research_pipeline.execute("https://example.com","Increase sales inquiries")
    assert result["source"] == "https://example.com"
    assert result["actions_executed"] == 0
    assert result["mode"] == "homepage_evidence"
    assert all(action["approval_required"] for action in result["plan"]["actions"])
