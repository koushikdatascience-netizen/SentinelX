"""Bounded opt-in Muse Image route. All paid Meta calls use MetaClient."""
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.auth import current_user
from app.workspace_store import User
from app.meta_client import MetaClient, MetaResponseError

router=APIRouter(prefix="/api/v1/creative",tags=["Creative"])

class ImagePrompt(BaseModel):
    prompt: str = Field(min_length=15,max_length=1500)
    size: str = Field(default="1024x1024",pattern=r"^(1024x1024|1024x1536|1536x1024)$")

@router.post("/generate")
def generate_image(body:ImagePrompt,user:User=Depends(current_user)):
    if user.is_demo or os.getenv("SENTINELX_MODE") != "live":
        return {"status":"demo","provenance":"sample","image":None,"prompt":body.prompt,
                "note":"No image generated; no external model invoked."}
    try:
        result=MetaClient().image(body.prompt,body.size)
        if result["provenance"]=="sample":
            return {"status":"demo","provenance":"sample","image":None,"prompt":body.prompt,
                    "note":"Paid multimodal inference is disabled."}
        return {"status":"completed","provenance":"live_meta","model":result["model"],
                "image_b64":result["data"]["image_b64"],
                "note":"One Meta image request completed; account billing must be reconciled separately."}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502,f"Muse Image failed ({type(exc).__name__})") from exc
