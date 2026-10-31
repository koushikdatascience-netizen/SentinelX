import json
from types import SimpleNamespace
from datetime import datetime,timezone
from app.knowledge import retrieve


def test_retrieval_finds_relevant_late_chunks_and_deduplicates_files():
    text="General workshop background. "*400+" Refund returns require the original invoice. "*20
    first=SimpleNamespace(id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",filename="policy.txt",sha256="hash",created_at=datetime.now(timezone.utc),metadata_json=json.dumps({"knowledge_text":text}))
    duplicate=SimpleNamespace(**{**first.__dict__,"id":"duplicate"})
    result=retrieve([first,duplicate],"refund returns",limit=2)
    assert len(result)==2 and all("Refund" in row["text"] for row in result)
    assert all(row["asset_id"]==first.id and row["origin"]=="user_supplied" and len(row["id"])<=20 for row in result)
    from app.business_research import insight_sources
    sources=insight_sources({"name":"Refund returns workshop"},[],[first])
    assert any(source["id"].startswith("K") and "Refund" in source["text"] for source in sources)
