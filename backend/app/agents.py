"""Auditable proposed-action planner. Plans do not execute anything."""
from pydantic import BaseModel, Field

class ProposedAction(BaseModel):
    agent: str
    action: str
    reason: str
    approval_required: bool = True
    status: str = "proposed"

class AuditPlan(BaseModel):
    source_url: str
    source_title: str
    evidence_excerpt: str
    confidence: str = "low"
    actions: list[ProposedAction] = Field(default_factory=list)

def build_plan(page: dict, goal: str) -> AuditPlan:
    return AuditPlan(
        source_url=page["evidence_source"],
        source_title=page["title"],
        evidence_excerpt=page["text"][:400],
        actions=[
            ProposedAction(agent="research", action="Investigate public competitors and positioning", reason="Competitive claims require independent sources"),
            ProposedAction(agent="seo", action="Review page titles and conversion messaging", reason="Compare website evidence with the stated goal"),
            ProposedAction(agent="creative", action="Prepare two campaign concepts", reason="Test ideas before requesting approval"),
        ],
    )
