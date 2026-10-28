"""Public, no-secrets capability status. Live requires recent actual completed call."""
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.workspace_store import MetaCapabilityCheck,session
from app.meta_client import MetaClient
import os

router=APIRouter(tags=["Status"])

@router.get("/api/v1/status")
def capability_status(db:Session=Depends(session)):
    modes={}
    ready=MetaClient._enabled(True)
    expected={"text":os.getenv("META_MODEL","muse-spark-1.3"),
              "vision":os.getenv("META_MODEL","muse-spark-1.3"),
              "image":"muse-image-1.0",
              "voice":"muse-voice-transcribe-1.0",
              "search":"muse-spark-1.3",
              "segmentation":"sam-3.1"}
    for name,model in expected.items():
        if name=="segmentation":
            modes[name]={"state":"UNAVAILABLE","model":model,"last_success_at":None,
                         "note":"SAM segmentation adapter is not implemented; no masks are generated"}
            continue
        row=db.get(MetaCapabilityCheck,name)
        checked=None
        fresh=False
        if row:
            date=row.succeeded_at
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            checked=date.isoformat()
            fresh=date>=datetime.now(timezone.utc)-timedelta(hours=24) and row.model==model
        actual=ready and fresh
        modes[name]={"state":"LIVE" if actual else "SAMPLE",
                     "model":model,
                     "last_success_at":checked,
                     "note":"Verified by a recent successful server request" if actual else
                            "Not recently live-verified for this model and deployment"}
    return {"capabilities":modes,
            "note":"A configured key or promotional credit balance alone does not prove runtime capability.",
            "automatic_publishing":False}
