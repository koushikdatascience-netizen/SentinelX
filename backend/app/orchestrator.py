"""Deterministic, offline-safe orchestration for the first SentinelX demo.

Agent outputs are mock tasks, NOT evidence of research or inference.
"""
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field
from app.model_registry import catalog

class TaskStep(BaseModel):
    id: str
    agent: str
    model: str
    status: Literal["pending","mock_completed","blocked"]
    detail: str
    evidence: list[str] = Field(default_factory=list)

class WorkflowPreview(BaseModel):
    run_id: str
    mode: Literal["mock"] = "mock"
    objective: str
    steps: list[TaskStep]
    approvals_needed: list[str]
    actual_external_actions: int = 0
    warning: str = "Simulated workflow. No models, pages or external services were called."

ASSIGNMENTS = [
    ("research", "muse-spark-1.3", "Identify what evidence and public sources to collect."),
    ("planner", "muse-wonder", "Compare realistic options and select testable next steps."),
    ("vision", "sam-3.1", "Request consented product imagery for a visual audit."),
    ("creative", "muse-image-1.0", "Draft two creative briefs for later generation."),
    ("voice", "muse-voice-transcribe-1.0", "Offer optional recorded business instructions."),
    ("private_reasoning", "muse-spark-open", "Provide an eligible open-weight inference route."),
    ("edge", "muse-glimmer", "Plan an optional small on-device inference task."),
]

def preview(goal: str) -> WorkflowPreview:
    _ = catalog()
    return WorkflowPreview(
        run_id=str(uuid4()),
        objective=goal,
        steps=[
            TaskStep(id=f"step-{index}",agent=agent,model=model,
                     status="mock_completed",detail=detail)
            for index,(agent,model,detail) in enumerate(ASSIGNMENTS,1)
        ],
        approvals_needed=["Publishing campaigns", "Changing business website or external accounts"],
    )
