"""Authenticated, tightly bounded inference smoke-test endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import current_user, owned_run
from app.workspace_store import session
from sqlalchemy.orm import Session
from app.workspace_store import User
from app.providers import configured_provider, infer
from app.budget import budget_status

router = APIRouter(prefix="/api/v1/inference", tags=["Inference"])

class InferenceRequest(BaseModel):
    workspace_id: str | None = None
    run_id: str | None = None
    prompt: str = Field(min_length=10,max_length=2000)

@router.get("/status")
def status(user: User = Depends(current_user)):
    try:
        config = configured_provider()
    except ValueError as exc:
        return {"configured":False,"provider":"invalid","note":str(exc)}
    return {"configured":config is not None,"provider":config.name if config else "demo",
            "model":config.model if config else None,"note":"Configured does not guarantee live availability or free remaining quota."}

@router.post("/test")
def test_inference(body: InferenceRequest, user: User = Depends(current_user), db: Session = Depends(session)):
    if body.workspace_id or body.run_id:
        owned_run(db,user,body.workspace_id,body.run_id)
    try:
        return infer(body.prompt, owner_id=getattr(user,"id",None), workspace_id=body.workspace_id, run_id=body.run_id)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502,f"Inference failed ({type(exc).__name__})") from exc

@router.get("/budget")
def app_budget(user: User = Depends(current_user)):
    return {"meta":budget_status("meta"),"openrouter":budget_status("openrouter"),"groq":budget_status("groq")}
