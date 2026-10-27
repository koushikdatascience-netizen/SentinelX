from app.agents import build_plan

def test_heuristics_are_grounded_in_supplied_excerpt():
    base={"evidence_source":"https://example.com","title":"Carpentry Demo"}
    plan=build_plan({**base,"text":"We offer handmade tables and chairs. WhatsApp us for a quote."},"Improve qualified inquiries")
    assert plan.confidence=="low"
    assert "contains contact-related" in plan.actions[0].reason
    assert "mentions prices or quotations" in plan.actions[1].reason
    assert all(a.approval_required and a.status=="proposed" for a in plan.actions)

def test_missing_terms_do_not_claim_full_site_absence():
    plan=build_plan({"evidence_source":"https://example.com","title":"Demo","text":"Custom wood furniture for home interiors."},"Improve inquiries")
    assert "supplied excerpt" in plan.actions[0].reason
    assert "complete page" in plan.actions[0].reason
    assert "full catalogue" in plan.actions[1].reason
