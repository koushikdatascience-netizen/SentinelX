"""Validated media inspection and scoped Meta vision; voice adapter unsupported.
No media is persisted in this prototype.
"""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.auth import current_user
from app.workspace_store import User
from PIL import Image, UnidentifiedImageError
from app.meta_client import MetaClient, NotSupported
from app.auth import owned_run
from app.workspace_store import session
from sqlalchemy.orm import Session

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
    return {"provenance":"user_supplied","filename":file.filename,"format":fmt,"width":width,"height":height,
            "bytes":len(payload),"inference":"not_run","note":"Image validated locally. SAM inference requires a separate explicit API call."}

@router.post("/voice/transcribe")
async def transcribe_audio(file:UploadFile=File(...),user:User=Depends(current_user)):
    payload=await file.read(MAX_AUDIO+1)
    if len(payload)>MAX_AUDIO: raise HTTPException(413,"Audio exceeds 10 MB")
    allowed={"audio/wav","audio/x-wav","audio/mpeg","audio/mp4","audio/ogg","audio/webm"}
    if file.content_type not in allowed: raise HTTPException(415,"Unsupported audio type")
    if not payload: raise HTTPException(422,"Empty recording")
    try:
        result=MetaClient().transcribe(payload,file.content_type)
        return {**result,"status":"demo","transcript":None,"note":"Sample intake only; no speech recognition performed."}
    except NotSupported as exc:
        raise HTTPException(501,str(exc)) from None


@router.post("/image/analyze")
def analyze_image(workspace_id:str,run_id:str,prompt:str="Describe visible product details without inventing business facts.",
                  file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(session)):
    owned_run(db,user,workspace_id,run_id)
    payload=file.file.read(MAX_IMAGE+1)
    try:
        return MetaClient(owner_id=user.id,workspace_id=workspace_id,run_id=run_id).vision(payload,file.content_type,prompt)
    except NotSupported as exc:
        raise HTTPException(501,str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
