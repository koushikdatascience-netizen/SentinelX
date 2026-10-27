import os
import uuid
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, HttpUrl
from app.workflows import State, ActionRecord, action_store
from app.auth import current_user

app = FastAPI(title="SentinelX API", version="0.4.0")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS","http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])

class RunRequest(BaseModel):
    website: HttpUrl
    goal: str = Field(min_length=10, max_length=1000)
    industry: str | None = None

class Finding(BaseModel):
    title: str
    detail: str
    confidence: Literal["unverified","low","medium","high"] = "unverified"

class RunResponse(BaseModel):
    run_id: str
    mode: Literal["demo","live"]
    status: str
    business_domain: str
    objective: str
    findings: list[Finding]
    recommended_actions: list[str]
    requires_approval: bool = True
    note: str

MAX_REQUESTS = int(os.getenv("MAX_LIVE_REQUESTS_PER_SESSION","5"))
counts = {"live_requests": 0}

@app.get("/health")
def health():
    return {"status":"ok","model":os.getenv("META_MODEL","muse-spark-1.3"),"mode":"live" if os.getenv("MODEL_API_KEY") and os.getenv("SENTINELX_MODE") == "live" else "demo"}

@app.post("/api/v1/analyze",response_model=RunResponse, dependencies=[Depends(current_user)])
def analyze(body: RunRequest):
    if os.getenv("ENABLE_LEGACY_ENDPOINTS") != "true":
        raise HTTPException(410,"Legacy endpoint disabled; use authenticated workspace API")
    run_id = str(uuid.uuid4())
    domain = urlparse(str(body.website)).hostname or ""
    if os.getenv("SENTINELX_MODE","demo") != "live":
        return RunResponse(run_id=run_id,mode="demo",status="completed",business_domain=domain,objective=body.goal,
            findings=[Finding(title="Digital presence review required",detail="Demo placeholder: website not crawled; claims not verified.")],
            recommended_actions=["Review homepage conversion messaging","Research relevant competitors","Prepare a measurable seven-day experiment"],
            note="Demonstration only. No external research or AI inference performed.")
    if os.getenv("ENABLE_LEGACY_META_ANALYZE") != "true":
        raise HTTPException(status_code=403,detail="Legacy paid inference disabled: use budgeted workspace inference")
    if not os.getenv("MODEL_API_KEY"):
        raise HTTPException(status_code=503,detail="MODEL_API_KEY missing")
    if counts["live_requests"] >= MAX_REQUESTS:
        raise HTTPException(status_code=429,detail="Local live request guard reached")
    counts["live_requests"] += 1
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.meta.ai/v1",api_key=os.environ["MODEL_API_KEY"],timeout=45.0,max_retries=0)
        prompt = ("You are a cautious business strategist. The supplied URL has NOT been fetched. "
                  "Never claim to have inspected the website. Identify assumptions. "
                  f"Website: {body.website}; Industry: {body.industry or 'unknown'}; Goal: {body.goal}")
        response = client.responses.create(model=os.getenv("META_MODEL","muse-spark-1.3"),input=prompt,max_output_tokens=550)
        detail = (getattr(response,"output_text","") or "No text returned")[:3500]
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f"Model API failed ({type(exc).__name__})") from exc
    return RunResponse(run_id=run_id,mode="live",status="completed",business_domain=domain,objective=body.goal,
        findings=[Finding(title="Preliminary AI assessment",detail=detail)],
        recommended_actions=["Research with citations","Review findings before actions","Define success metric"],
        note="Model assessment only. Website has not been fetched.")

class ResearchResponse(BaseModel):
    run_id: str
    status: str
    plan: dict
    note: str

@app.post("/api/v1/research",response_model=ResearchResponse, dependencies=[Depends(current_user)])
def research(body: RunRequest):
    if os.getenv("ENABLE_LEGACY_ENDPOINTS") != "true":
        raise HTTPException(410,"Legacy endpoint disabled; use authenticated workspace API")
    from app.research import snapshot
    from app.agents import build_plan
    try:
        page = snapshot(str(body.website))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f"Website retrieval failed ({type(exc).__name__})") from exc
    return ResearchResponse(run_id=str(uuid.uuid4()),status="proposed",plan=build_plan(page,body.goal).model_dump(),
        note="Only supplied homepage retrieved. No competitor research, forecast or action execution.")

class ProposalRequest(BaseModel):
    run_id: str = Field(min_length=1,max_length=100)
    kind: Literal["seo","research","creative","campaign"]
    description: str = Field(min_length=10,max_length=1000)
    source_url: HttpUrl

class ReviewRequest(BaseModel):
    decision: Literal["approved","rejected"]

@app.post("/api/v1/actions",response_model=ActionRecord,status_code=201, dependencies=[Depends(current_user)])
def propose_action(body: ProposalRequest):
    if os.getenv("ENABLE_LEGACY_ENDPOINTS") != "true":
        raise HTTPException(410,"Legacy endpoint disabled; use authenticated workspace API")
    return action_store.propose(body.run_id,body.kind,body.description,str(body.source_url))

@app.get("/api/v1/actions/{action_id}",response_model=ActionRecord, dependencies=[Depends(current_user)])
def get_action(action_id: str):
    if os.getenv("ENABLE_LEGACY_ENDPOINTS") != "true":
        raise HTTPException(410,"Legacy endpoint disabled; use authenticated workspace API")
    record = action_store.get(action_id)
    if record is None:
        raise HTTPException(status_code=404,detail="Action not found")
    return record

@app.post("/api/v1/actions/{action_id}/review",response_model=ActionRecord, dependencies=[Depends(current_user)])
def review_action(action_id: str,body: ReviewRequest):
    if os.getenv("ENABLE_LEGACY_ENDPOINTS") != "true":
        raise HTTPException(410,"Legacy endpoint disabled; use authenticated workspace API")
    try:
        rec = action_store.decide(action_id,State(body.decision))
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    if rec is None:
        raise HTTPException(status_code=404,detail="Action not found")
    return rec


@app.get("/api/v1/models")
def list_model_capabilities():
    from app.model_registry import catalog
    configured = os.getenv("META_MODEL") if os.getenv("MODEL_API_KEY") else None
    return {"models":[item.model_dump() for item in catalog(configured)],
            "note":"Configured does not mean authorized, reachable or tested."}

@app.post("/api/v1/workflows/preview", dependencies=[Depends(current_user)])
def preview_workflow(body: RunRequest):
    from app.orchestrator import preview
    return preview(body.goal)

# Authenticated workspace API (isolated from legacy prototype routes).
from app.workspace_routes import router as workspace_router
from app.workspace_store import init_db
from app.budget import ApiBudget
from app.meta_adapters import capabilities
app.include_router(workspace_router)

@app.on_event("startup")
def initialize_workspace_database():
    init_db()

@app.get("/api/v1/meta/capabilities")
def meta_capability_status():
    return {"capabilities": [item.model_dump() for item in capabilities()]}

from app.media_routes import router as media_router
app.include_router(media_router)

from app.creative_routes import router as creative_router
app.include_router(creative_router)

from app.inference_routes import router as inference_router
app.include_router(inference_router)

from app.evidence_routes import router as evidence_router
app.include_router(evidence_router)

@app.get("/api/v1/meta/readiness",dependencies=[Depends(current_user)])
def get_meta_readiness():
    from app.model_registry import integration_readiness
    return {"integrations":integration_readiness(),"mode":"not_verified",
            "warning":"Credit activation, provider access and actual live calls are not confirmed."}
