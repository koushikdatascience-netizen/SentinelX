"""Workspace-owned validated product photo scores. No persistent photo blobs yet."""
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import ImageAssessment, User, session
from app.image_scoring import measure_image
from app.meta_client import MetaClient, MetaResponseError

router=APIRouter(prefix="/api/v1/images",tags=["Images"])

class Scores(BaseModel):
    model_config=ConfigDict(extra="forbid")
    score_lighting: int=Field(ge=0,le=100)
    score_composition: int=Field(ge=0,le=100)
    score_clarity: int=Field(ge=0,le=100)
    score_background: int=Field(ge=0,le=100)
    score_offer_fit: int=Field(ge=0,le=100)
    overall: int=Field(ge=0,le=100)
    strengths: list[str]=Field(max_length=5)
    issues: list[str]=Field(max_length=5)
    fixes: list[str]=Field(max_length=5)
    verdict: str=Field(min_length=3,max_length=240)

@router.post("/score",status_code=201)
async def score_photo(workspace_id:str=Form(...),business_context:str=Form(""),
                      file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    if len(business_context)>1500: raise HTTPException(422,"Business context too long")
    payload=await file.read(5_000_001)
    try: local=measure_image(payload)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    # The declared MIME must match the parsed file format, not just be on an allowlist.
    if file.content_type != {"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp"}[local["format"]]:
        raise HTTPException(415,"Unsupported content type")
    schema=Scores.model_json_schema()
    prompt=("Assess this consented product image for marketing use, relative to the business description. "
            "Give concrete suggestions; do not claim sales outcomes or unobserved facts. "
            f"Business description: {business_context}")
    try:
        result=(MetaClient().vision(payload,file.content_type,prompt,schema)
                if not user.is_demo else {"provenance":"sample","data":{"note":"Demo sessions cannot call paid models"}})
        model_scores=Scores.model_validate(result["data"]).model_dump() if result["provenance"]=="live_meta" else None
    except (ValueError,MetaResponseError) as exc:
        raise HTTPException(502,"Meta vision returned invalid scores; no automatic retry") from exc
    except Exception as exc:
        raise HTTPException(502,f"Meta vision unavailable ({type(exc).__name__})") from exc
    # Local brightness, contrast and texture aren't calibrated 0-100 aesthetic scores.
    # Never combine unrelated scales or fabricate model scores.
    output={"local":local,"model":model_scores,
            "provenance":"live_meta" if model_scores else "local_measurement",
            "segmentation":"not_run","final_score":model_scores["overall"] if model_scores else None,
            "note":"Final score is the Meta subjective model score, not independently validated quality or predicted revenue."}
    row=ImageAssessment(workspace_id=workspace_id,filename=(file.filename or "image")[:180],
                        assessment_json=json.dumps(output))
    db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"workspace_id":workspace_id,"filename":row.filename,"result":output}

@router.get("/{image_id}")
def get_assessment(image_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    row=db.scalar(select(ImageAssessment).where(ImageAssessment.id==image_id,ImageAssessment.workspace_id==workspace_id))
    if row is None: raise HTTPException(404,"Image assessment not found")
    return {"id":row.id,"workspace_id":workspace_id,"filename":row.filename,"result":json.loads(row.assessment_json)}

@router.delete("/{image_id}",status_code=204)
def delete_assessment(image_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    row=db.scalar(select(ImageAssessment).where(ImageAssessment.id==image_id,ImageAssessment.workspace_id==workspace_id))
    if row is None: raise HTTPException(404,"Image assessment not found")
    db.delete(row);db.commit()
