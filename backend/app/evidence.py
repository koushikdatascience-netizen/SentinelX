"""Deterministic evidence quality checks for agent-generated recommendations."""
from pydantic import BaseModel, Field, HttpUrl

class Evidence(BaseModel):
    url: HttpUrl
    excerpt: str = Field(min_length=10,max_length=2000)
    collected: bool = False

class Recommendation(BaseModel):
    claim: str = Field(min_length=10,max_length=1500)
    evidence: list[Evidence] = Field(default_factory=list)
    action: str = Field(min_length=10,max_length=1500)

def assess(recommendation: Recommendation) -> dict:
    reviewed = [e for e in recommendation.evidence if e.collected]
    return {
        "claim":recommendation.claim,
        "action":recommendation.action,
        "status":"evidence_supported" if reviewed else "unverified",
        "usable_sources":[str(e.url) for e in reviewed],
        "approval_required":True,
        "execution_performed":False,
        "note":"Source presence does not prove a claim; human review remains required."
    }
