"""Opt-in Muse Image generation. No automatic API spending."""
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.auth import current_user
from app.workspace_store import User

router=APIRouter(prefix="/api/v1/creative",tags=["Creative"])

class ImagePrompt(BaseModel):
    prompt: str = Field(min_length=15,max_length=1500)
    size: str = Field(default="1024x1024",pattern=r"^(1024x1024|1024x1536|1536x1024)$")

@router.post("/generate")
def generate_image(body:ImagePrompt,user:User=Depends(current_user)):
    if os.getenv("SENTINELX_MODE")!="live":
        return {"status":"demo","image":None,"prompt":body.prompt,
                "note":"No image was generated; enable live mode only with a funded key and approved budget."}
    key=os.getenv("MODEL_API_KEY")
    if not key: raise HTTPException(503,"MODEL_API_KEY not configured")
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key,base_url="https://api.meta.ai/v1",timeout=60,max_retries=0)
        result=client.images.generate(model="muse-image-1.0",prompt=body.prompt,size=body.size,n=1)
        item=result.data[0]
        return {"status":"completed","image_b64":getattr(item,"b64_json",None),
                "image_url":getattr(item,"url",None),
                "note":"One paid image generation request completed."}
    except Exception as exc:
        raise HTTPException(502,f"Muse Image request failed ({type(exc).__name__})") from exc
