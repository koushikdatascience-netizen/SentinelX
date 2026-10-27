"""Validated media inspection; opt-in real Muse Voice transcription.
No media is persisted in this prototype.
"""
import io
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.auth import current_user
from app.workspace_store import User
from PIL import Image, UnidentifiedImageError
import httpx

router=APIRouter(prefix="/api/v1/media",tags=["Media"])
MAX_IMAGE=5_000_000
MAX_AUDIO=10_000_000

@router.post("/image/inspect")
async def inspect_image(file:UploadFile=File(...),user:User=Depends(current_user)):
    payload=await file.read(MAX_IMAGE+1)
    if len(payload)>MAX_IMAGE: raise HTTPException(413,"Image exceeds 5 MB")
    try:
        with Image.open(io.BytesIO(payload)) as im:
            if im.format not in ("PNG","JPEG","WEBP"): raise HTTPException(415,"Unsupported image format")
            width,height=im.size
            if width*height>20_000_000: raise HTTPException(413,"Too many pixels")
            im.verify()
            fmt=im.format
    except Image.DecompressionBombError:
        raise HTTPException(413,"Too many pixels")
    except (UnidentifiedImageError,OSError,ValueError):
        raise HTTPException(415,"Invalid image data")
    return {"filename":file.filename,"format":fmt,"width":width,"height":height,
            "bytes":len(payload),"inference":"not_run","note":"Image validated locally. SAM inference requires a separate explicit API call."}

@router.post("/voice/transcribe")
async def transcribe_audio(file:UploadFile=File(...),user:User=Depends(current_user)):
    payload=await file.read(MAX_AUDIO+1)
    if len(payload)>MAX_AUDIO: raise HTTPException(413,"Audio exceeds 10 MB")
    allowed={"audio/wav","audio/x-wav","audio/mpeg","audio/mp4","audio/ogg","audio/webm"}
    if file.content_type not in allowed: raise HTTPException(415,"Unsupported audio type")
    if not payload: raise HTTPException(422,"Empty recording")
    if user.is_demo or os.getenv("SENTINELX_MODE")!="live":
        return {"status":"demo","transcript":None,"note":"Audio upload accepted; transcription was not run."}
    if os.getenv("ENABLE_LIVE_MULTIMODAL") != "true":
        raise HTTPException(403,"Live multimodal calls disabled pending verified metering and approved billing limits")
    key=os.getenv("MODEL_API_KEY")
    if not key: raise HTTPException(503,"Meta Model API key not configured")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response=await client.post("https://api.meta.ai/v1/asr/transcribe",
                headers={"Authorization":f"Bearer {key}"},
                files={"file":(file.filename or "recording.wav",payload,file.content_type)},
                data={"model":"muse-voice-transcribe-1.0"})
            response.raise_for_status()
            return {"status":"completed","result":response.json()}
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(502,f"Meta transcription request failed ({type(exc).__name__})") from exc
