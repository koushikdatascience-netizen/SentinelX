from app.orchestrator import preview
from app.model_registry import catalog,Availability

def test_all_model_families_represented():
    plan = preview("Increase inquiries from nearby customers")
    assert len(plan.steps) == 7
    assert len({step.model for step in plan.steps}) == 7
    assert plan.actual_external_actions == 0
    assert plan.mode == "mock"
    assert all(not step.evidence for step in plan.steps)

def test_registry_honest_access():
    listed = catalog("muse-spark-1.3")
    assert len(listed) == 7
    assert listed[0].access == Availability.configured
    assert all(item.access == Availability.mock for item in listed[1:])
