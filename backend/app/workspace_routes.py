"""Authenticated, owner-scoped workspace APIs. No automatic external execution."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth import current_user, hash_password, check_password, issue_token
from app.workspace_store import User, Workspace, WorkflowRun, session

router=APIRouter(prefix="/api/v1",tags=["Workspaces"])

class Credentials(BaseModel):
    email: str = Field(min_length=3,max_length=255,pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10,max_length=72)
class WorkspaceInput(BaseModel):
    name: str = Field(min_length=2,max_length=160)
class RunInput(BaseModel):
    website: HttpUrl
    goal: str = Field(min_length=10,max_length=1000)
    use_inference: bool = False

@router.post("/auth/register",status_code=201)
def register(body:Credentials,db:Session=Depends(session)):
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
