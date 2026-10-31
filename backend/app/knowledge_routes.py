"""Owner-scoped knowledge extraction and deterministic data tools."""
import hashlib
import json
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import User,WorkflowRun,session
from app.business_store import BrandAsset,BusinessProfile
from app.business_files import asset_info
from app.business_data import DataQuery,calculate
from app.campaign_routes import generation_is_live
from app.workbench import begin,serialize,extract_document,DocumentError
from app.document_meta import extract_scans
from app.meta_client import MetaError

router=APIRouter(tags=["Business knowledge"])


def knowledge_asset(db,user,wid,aid):
    owned(db,user,wid)
    asset=db.scalar(select(BrandAsset).where(BrandAsset.id==aid,BrandAsset.workspace_id==wid,BrandAsset.kind.in_(["document","knowledge"])))
    if not asset:raise HTTPException(404,"Knowledge document not found")
    if hashlib.sha256(asset.content).hexdigest()!=asset.sha256:raise HTTPException(422,"Saved knowledge file integrity check failed")
    return asset


class KnowledgeRead(BaseModel):
    request_id:UUID
    consent:bool=False
    start_page:int=Field(default=1,ge=1,le=2000)
    page_limit:int=Field(default=5,ge=1,le=5)


@router.post("/api/v1/workspaces/{wid}/knowledge/{aid}/read")
def read_knowledge(wid:str,aid:str,body:KnowledgeRead,user:User=Depends(current_user),db:Session=Depends(session)):
    asset=knowledge_asset(db,user,wid,aid);profile=db.get(BusinessProfile,wid)
    if not body.consent or not profile or not profile.consent_at:raise HTTPException(422,"Consent to send selected scanned pages to Meta and save their text is required")
    if asset.mime!="application/pdf":raise HTTPException(422,"Only scanned PDF pages require this Meta-reading action")
    signature=hashlib.sha256(f"{aid}:{asset.sha256}:{body.start_page}:{body.page_limit}".encode()).hexdigest()
    row,reused=begin(db,user,wid,body.request_id,"knowledge_extract",signature)
    if reused:return serialize(row)
    result=json.loads(row.result_json);metadata=json.loads(asset.metadata_json);cached=metadata.get("meta_pages",{})
    failure_status=502
    try:
        data=extract_document(asset.content,asset.filename,body.start_page,body.page_limit)
        for page in data["pages"]:
            if str(page["page"]) in cached:page.update(cached[str(page["page"])])
        missing=[page for page in data["pages"] if page["needs_ocr"] and str(page["page"]) not in cached]
        if len(cached)+len(missing)>100 or sum(len(page["text"]) for page in cached.values())+20000*len(missing)>400000:raise ValueError("Knowledge cache limit; choose a smaller page batch")
        if missing:
            generation_is_live(user,"live")
            reply=extract_scans(asset.content,{"pages":missing},user.id,wid,row.id)
            result.update(provenance="live_meta",model=reply["model"]);metadata.update(text_processing="live_meta",text_model=reply["model"])
        if any(page.get("provenance")=="live_meta" for page in data["pages"]):result.update(provenance="live_meta",model=metadata.get("text_model","muse-spark-1.3"))
        for page in data["pages"]:cached[str(page["page"])]=page
        if len(cached)>100 or sum(len(page["text"]) for page in cached.values())>400000:raise ValueError("Knowledge PDF text cache is full; split this document into smaller files")
        metadata["meta_pages"]=cached
        combined={**metadata.get("page_texts",{}),**{number:page["text"] for number,page in cached.items()}}
        metadata["knowledge_text"]="\n\n".join(f"Page {number}\n{combined[number]}" for number in sorted(combined,key=int))[:80000]
        metadata["text_excerpt"]=metadata["knowledge_text"][:8000]
        metadata["cached_pages"]=len(cached);asset.metadata_json=json.dumps(metadata,ensure_ascii=False)
        result.update(data=data,asset_id=asset.id);row.status="completed"
    except Exception as exc:
        db.rollback();row.status="failed"
        result["error"]="Knowledge extraction stopped. Saved text is unchanged; no automatic paid retry. Check Meta configuration, page size and budget."
        if isinstance(exc,ValueError) and str(exc).startswith("Meta budget reached"):failure_status=429;result["error"]="Meta budget reached; no automatic retry. Existing knowledge remains saved."
        elif isinstance(exc,DocumentError):failure_status=422;result["error"]=str(exc)
        elif isinstance(exc,HTTPException):failure_status=exc.status_code;result["error"]=exc.detail
    row.result_json=json.dumps(result,ensure_ascii=False);db.commit()
    if row.status=="failed":raise HTTPException(failure_status,result["error"])
    return serialize(row)


@router.post("/api/v1/workspaces/{wid}/knowledge/{aid}/analyze")
def analyze_knowledge(wid:str,aid:str,body:DataQuery,user:User=Depends(current_user),db:Session=Depends(session)):
    asset=knowledge_asset(db,user,wid,aid)
    try:return calculate(asset.content,asset.filename,body)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
