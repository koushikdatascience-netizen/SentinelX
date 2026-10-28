import pytest
from app.mission import CitationMismatch,sample_source,report_markdown,sample_plan
from app.mission_research import sample_research,validate_research


def test_research_requires_known_source_and_preserves_negation():
    research=sample_research()
    assert validate_research(research,[sample_source()])==research
    research["findings"][0]["source_id"]="S99"
    with pytest.raises(CitationMismatch):validate_research(research,[sample_source()])
    research["findings"][0].update(source_id="S1",quote="We do not build custom furniture.")
    with pytest.raises(CitationMismatch):validate_research(research,[sample_source()])


def test_export_includes_only_validated_research():
    payload={"provenance":"sample","sources":[sample_source()],"plan":sample_plan(),
        "research":{"provenance":"sample","validated":False,"data":sample_research()}}
    assert "## Research handoff" not in report_markdown(payload)
    payload["research"]["validated"]=True
    text=report_markdown(payload)
    assert "## Research handoff" in text and "Planning constraint:" in text
    assert "not independent verification" in text
