"""Typed research handoff; cited observations remain unverified source claims."""
from typing import Annotated
from pydantic import BaseModel,ConfigDict,Field
from app.mission import CitationMismatch,normalize_quote


class ResearchFinding(BaseModel):
    model_config=ConfigDict(extra="forbid")
    source_id:str=Field(min_length=2,max_length=20)
    quote:str=Field(min_length=12,max_length=240)
    observation:str=Field(min_length=15,max_length=250)
    planning_constraint:str=Field(min_length=15,max_length=250)


class ResearchBrief(BaseModel):
    model_config=ConfigDict(extra="forbid")
    findings:list[ResearchFinding]=Field(min_length=1,max_length=3)
    unknowns:list[Annotated[str,Field(min_length=1,max_length=250)]]=Field(min_length=1,max_length=5)


def validate_research(data,sources):
    brief=ResearchBrief.model_validate(data)
    evidence={source["id"]:normalize_quote(source["text"]) for source in sources}
    for item in brief.findings:
        if item.source_id not in evidence or normalize_quote(item.quote) not in evidence[item.source_id]:
            raise CitationMismatch("Research quote does not match the collected source")
    return brief.model_dump()


def sample_research():
    return {"findings":[{"source_id":"S1","quote":"We build custom furniture.",
        "observation":"The sample source describes a custom furniture offering.",
        "planning_constraint":"Preserve the existing custom offering; do not invent prices or delivery times."}],
        "unknowns":["Customer demand and conversion outcomes are unknown in this authored sample."]}
