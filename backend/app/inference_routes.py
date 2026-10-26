"""Authenticated, tightly bounded inference smoke-test endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import current_user
from app.workspace_store import User
from app.providers import configured_provider, infer

router = APIRouter(prefix="/api/v1/inference", tags=["Inference"])

class InferenceRequest(BaseModel):
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
def test_inference(body: InferenceRequest, user: User = Depends(current_user)):
    try:
        return infer(body.prompt)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502,f"Inference failed ({type(exc).__name__})") from exc
