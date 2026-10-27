"""Owned-run image generation through the only Meta transport."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth import current_user, owned_run
from app.workspace_store import User, session
from app.meta_client import MetaClient, NotSupported

router=APIRouter(prefix="/api/v1/creative",tags=["Creative"])

class ImagePrompt(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=36)
    run_id: str = Field(min_length=1, max_length=36)
    prompt: str = Field(min_length=15,max_length=1500)
    size: str = Field(default="1024x1024",pattern=r"^(1024x1024|1024x1536|1536x1024)$")

@router.post("/generate")
def generate_image(body:ImagePrompt,user:User=Depends(current_user),db:Session=Depends(session)):
    owned_run(db,user,body.workspace_id,body.run_id)
    try:
        result=MetaClient(owner_id=user.id,workspace_id=body.workspace_id,run_id=body.run_id).image(body.prompt,body.size)
        return {**result,"status":"completed" if result["provenance"]=="live_meta" else "demo",
                "note":"Internal artifact only. No external publishing occurred."}
    except NotSupported as exc:
        raise HTTPException(501,str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
