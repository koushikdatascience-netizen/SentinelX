"""Authenticated, owner-scoped workspace APIs. No automatic external execution."""
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth import current_user, hash_password, check_password, issue_token
from app.workspace_store import User, Workspace, WorkflowRun, ReviewableAction, utcnow, session

router=APIRouter(prefix="/api/v1",tags=["Workspaces"])

class Credentials(BaseModel):
    email: str = Field(min_length=3,max_length=255,pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10,max_length=72)

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must fit within 72 UTF-8 bytes")
        return value
class WorkspaceInput(BaseModel):
    name: str = Field(min_length=2,max_length=160)
class RunInput(BaseModel):
    website: HttpUrl
    goal: str = Field(min_length=10,max_length=1000)
    use_inference: bool = False

@router.post("/auth/register",status_code=201)
def register(body:Credentials,db:Session=Depends(session)):
    # Local development permits signup; staging explicitly closes it unless invited.
    allowed = {email.strip().lower() for email in os.getenv("REGISTRATION_ALLOWED_EMAILS", "").split(",") if email.strip()}
    if os.getenv("ALLOW_PUBLIC_REGISTRATION", "true").lower() != "true" and body.email.lower() not in allowed:
        raise HTTPException(403,"Registration is restricted. Contact the workspace operator.")
    user=User(email=body.email.lower(),password_hash=hash_password(body.password))
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Email already registered")
    return {"id":user.id,"email":user.email}
@router.post("/auth/login")
def login(body:Credentials,db:Session=Depends(session)):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not check_password(body.password,user.password_hash):
        raise HTTPException(401,"Invalid credentials")
    return {"access_token":issue_token(user.id),"token_type":"bearer"}
@router.get("/workspaces")
def list_workspaces(user:User=Depends(current_user),db:Session=Depends(session)):
    return [{"id":w.id,"name":w.name} for w in db.scalars(select(Workspace).where(Workspace.owner_id==user.id)).all()]
@router.post("/workspaces",status_code=201)
def create_workspace(body:WorkspaceInput,user:User=Depends(current_user),db:Session=Depends(session)):
    obj=Workspace(owner_id=user.id,name=body.name)
    db.add(obj);db.commit();db.refresh(obj)
    return {"id":obj.id,"name":obj.name}
def owned(db:Session,user:User,workspace_id:str)->Workspace:
    workspace=db.scalar(select(Workspace).where(Workspace.id==workspace_id,Workspace.owner_id==user.id))
    if not workspace: raise HTTPException(404,"Workspace not found")
    return workspace
@router.get("/workspaces/{workspace_id}/runs")
def list_runs(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    return [{"id":r.id,"website":r.website,"goal":r.objective,"status":r.status} for r in db.scalars(select(WorkflowRun).where(WorkflowRun.workspace_id==workspace_id)).all()]
@router.post("/workspaces/{workspace_id}/runs",status_code=201)
def create_run(workspace_id:str,body:RunInput,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    from app.orchestrator import preview
    if body.use_inference:
        from app.providers import infer
        try:
            result=infer(f"Business website URL (not crawled): {body.website}\\nBusiness goal: {body.goal}\\nDevelop three testable recommendations. Clearly label assumptions.")
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502,f"Inference provider failed ({type(exc).__name__})") from exc
        status = "inferred" if result["status"]=="completed" else "mock_completed"
    else:
        result=preview(body.goal).model_dump()
        status="mock_completed"
    run=WorkflowRun(workspace_id=workspace_id,website=str(body.website),objective=body.goal,status=status,result_json=json.dumps(result))
    db.add(run);db.commit();db.refresh(run)
    return {"id":run.id,"workspace_id":workspace_id,"status":run.status,"result":result}
@router.get("/workspaces/{workspace_id}/runs/{run_id}")
def get_run(workspace_id:str,run_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    run=db.scalar(select(WorkflowRun).where(WorkflowRun.id==run_id,WorkflowRun.workspace_id==workspace_id))
    if not run: raise HTTPException(404,"Run not found")
    return {"id":run.id,"status":run.status,"website":run.website,"goal":run.objective,"result":json.loads(run.result_json)}

class EvidenceRunInput(BaseModel):
    website: HttpUrl
    goal: str = Field(min_length=10,max_length=1000)
    page_title: str = Field(min_length=1,max_length=200)
    page_excerpt: str = Field(min_length=25,max_length=8000)

@router.post("/workspaces/{workspace_id}/evidence-analysis",status_code=201)
def analyze_supplied_evidence(workspace_id:str,body:EvidenceRunInput,user:User=Depends(current_user),db:Session=Depends(session)):
    """No crawling or AI claim: owner-supplied page text, auditable proposals, persisted result."""
    owned(db,user,workspace_id)
    from app.agents import build_plan
    page={"evidence_source":str(body.website),"title":body.page_title,"text":body.page_excerpt}
    plan=build_plan(page,body.goal).model_dump()
    evidence={"source_url":str(body.website),"source_type":"user_supplied_unverified","excerpt":body.page_excerpt[:400],
              "fetched_by_server":False}
    result={"mode":"owner_supplied_evidence","evidence":[evidence],"plan":plan,
            "approval_required":True,"external_actions_performed":0}
    run=WorkflowRun(workspace_id=workspace_id,website=str(body.website),objective=body.goal,
                    status="proposed",result_json=json.dumps(result))
    db.add(run);db.commit();db.refresh(run)
    return {"id":run.id,"workspace_id":workspace_id,"status":run.status,"result":result}

class ActionInput(BaseModel):
    description: str = Field(min_length=10,max_length=1200)

class ActionDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")

@router.get("/workspaces/{workspace_id}/runs/{run_id}/actions")
def actions_for_run(workspace_id:str,run_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    run=db.scalar(select(WorkflowRun).where(WorkflowRun.id==run_id,WorkflowRun.workspace_id==workspace_id))
    if not run: raise HTTPException(404,"Run not found")
    return [{"id":a.id,"description":a.description,"state":a.state,"created_at":a.created_at.isoformat()} for a in db.scalars(select(ReviewableAction).where(ReviewableAction.run_id==run_id)).all()]

@router.post("/workspaces/{workspace_id}/runs/{run_id}/actions",status_code=201)
def new_action(workspace_id:str,run_id:str,body:ActionInput,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    run=db.scalar(select(WorkflowRun).where(WorkflowRun.id==run_id,WorkflowRun.workspace_id==workspace_id))
    if not run: raise HTTPException(404,"Run not found")
    action=ReviewableAction(run_id=run.id,description=body.description)
    db.add(action);db.commit();db.refresh(action)
    return {"id":action.id,"description":action.description,"state":action.state,"executed":False}

@router.post("/workspaces/{workspace_id}/actions/{action_id}/review")
def decide_action(workspace_id:str,action_id:str,body:ActionDecision,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    action=db.scalar(select(ReviewableAction).join(WorkflowRun,ReviewableAction.run_id==WorkflowRun.id).where(
        ReviewableAction.id==action_id,WorkflowRun.workspace_id==workspace_id))
    if not action: raise HTTPException(404,"Action not found")
    # Compare and set in the database so two workers cannot overwrite a decision.
    changed = db.execute(update(ReviewableAction).where(
        ReviewableAction.id == action.id, ReviewableAction.state == "proposed"
    ).values(state=body.decision, reviewed_at=utcnow()))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409,"Action was already reviewed")
    db.commit()
    db.refresh(action)
    return {"id":action.id,"description":action.description,"state":action.state,"executed":False,
            "note":"Approval is a recorded decision only. No external action has been executed."}

@router.get("/workspaces/{workspace_id}/runs/{run_id}/report")
def export_audit_report(workspace_id:str,run_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    """Export owner-only Markdown with honest provenance and no executed-action claims."""
    owned(db,user,workspace_id)
    run=db.scalar(select(WorkflowRun).where(WorkflowRun.id==run_id,WorkflowRun.workspace_id==workspace_id))
    if not run: raise HTTPException(404,"Run not found")
    payload=json.loads(run.result_json)
    notes=[
        "# SentinelX | Business Intelligence Audit",
        "",
        f"Run: {run.id}",
        f"Website: {run.website}",
        f"Objective: {run.objective}",
        f"Status: {run.status}",
        "",
        "## Evidence and provenance",
    ]
    sources=payload.get("evidence") or []
    if sources:
        for e in sources:
            notes.extend([f"- Source: {e.get('source_url','not specified')}",f"  - Type: {e.get('source_type','unverified')}",f"  - Quote: {e.get('excerpt','not available')}"])
    else: notes.append("No collected source evidence in this run. Simulation or model-generated assumptions may appear below.")
    notes.extend(["","## Findings and next steps"])
    plan=payload.get("plan") or {}
    actions=plan.get("actions") or []
    if actions:
        for a in actions: notes.append(f"- {a.get('agent','agent')}: {a.get('action','proposal')} — {a.get('reason','Review required')}")
    elif payload.get("text"): notes.append(str(payload["text"])[:10000])
    else: notes.append("No verified recommendations. Inspect the workflow result.")
    notes.extend(["","## Review decisions"])
    reviews=db.scalars(select(ReviewableAction).where(ReviewableAction.run_id==run_id)).all()
    for a in reviews: notes.append(f"- {a.description}: {a.state} (no external execution)")
    if not reviews: notes.append("No action decisions recorded.")
    notes.extend(["","## Limitations","This report does not claim verified business impact, competitor research, publishing, or model inference unless explicitly evidenced.",""])
    return Response(content="\n".join(notes),media_type="text/markdown",
                    headers={"Content-Disposition":f'attachment; filename="sentinelx-{run.id}.md"'})
