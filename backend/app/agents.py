"""Source-bound deterministic recommendations for the no-credit hackathon demo.

No competitor or business claim is treated as verified without independent sources.
"""
import re
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
    text=page.get("text","")
    normalized=re.sub(r"\s+"," ",text).lower()
    # These are text-presence observations, NOT proof that elements are absent
    # from the real website (the excerpt may not represent the entire page).
    contact_terms=("contact","call us","phone","whatsapp","request a quote","get a quote","book","enquire","inquire")
    pricing_terms=("price","pricing","starting at","₹","rs.","quote")
    has_contact=any(token in normalized for token in contact_terms)
    has_pricing=any(token in normalized for token in pricing_terms)
    actions=[
        ProposedAction(
            agent="conversion",
            action="Review the consultation or contact call-to-action against the stated goal",
            reason="The supplied excerpt "+("contains contact-related language; verify its prominence in the rendered site." if has_contact else "does not show contact-related language; inspect the complete page before concluding it is absent.")
        ),
        ProposedAction(
            agent="offer",
            action="Review pricing clarity, project scope and quotation expectations",
            reason="The supplied excerpt "+("mentions prices or quotations; assess whether customers can understand the next step." if has_pricing else "does not show prices or quotations; confirm against the full catalogue before recommending changes.")
        ),
        ProposedAction(
            agent="research",
            action="Gather independently sourced competitor and customer evidence before claiming market differences",
            reason="Only the owner-supplied excerpt is available; competitor comparisons and sales impact are unverified."
        )
    ]
    return AuditPlan(
        source_url=page["evidence_source"],source_title=page["title"],
        evidence_excerpt=text[:400],confidence="low",actions=actions
    )
