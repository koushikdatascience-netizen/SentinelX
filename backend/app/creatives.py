"""Source-attributed, locally storable creative variants. No social publishing."""
import base64
import hashlib
import io
import json
from typing import Literal
from uuid import UUID
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw

from app.auth import current_user
from app.workspace_routes import owned, create_model_run, finish_model_run
from app.workspace_store import User, CampaignCreative, CampaignItem, CampaignProject, WorkflowRun,ApprovalRecord,session
from app.image_scoring import measure_image
from app.meta_client import MetaClient

router=APIRouter(tags=["Creatives"])

class RequestVariants(BaseModel):
    variants: int=Field(default=2,ge=1,le=3)
    brand_mood: str=Field(default="warm, polished, natural",min_length=3,max_length=100)
    generation_mode: Literal["auto","sample","live"]="auto"
    prompt_override:str|None=Field(default=None,min_length=15,max_length=1000)
    request_id:UUID|None=None
    evaluate:bool=True

class BriefMatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    brief_match: int=Field(ge=0,le=100)
    reasons: list[str]=Field(min_length=1,max_length=5)

def scope(db:Session,wid:str,cid:str,iid:str,user:User):
    owned(db,user,wid)
    c=db.scalar(select(CampaignProject).where(CampaignProject.id==cid,CampaignProject.workspace_id==wid))
    i=db.scalar(select(CampaignItem).where(CampaignItem.id==iid,CampaignItem.campaign_id==cid))
    if c is None or i is None:raise HTTPException(404,"Campaign item not found")
    return c,i

def sample_gradient(seed:str)->bytes:
    digest=hashlib.sha256(seed.encode()).digest()
    top=(35+digest[0]//3,35+digest[1]//3,40+digest[2]//3)
    bottom=(45+digest[3]//3,40+digest[4]//3,65+digest[5]//3)
    im=Image.new("RGB",(768,768))
    pix=im.load()
    for y in range(768):
        t=y/767.0
        row=tuple(int(a*(1-t)+b*t) for a,b in zip(top,bottom))
        for x in range(768):pix[x,y]=row
    draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((85,210,683,560),radius=28,fill=(255,255,255),outline=(230,230,230),width=3)
    draw.text((290,360),"SAMPLE",fill=(40,35,60))
    draw.text((180,594),"Illustrative concept, not a product photo",fill=(248,244,250))
    stream=io.BytesIO()
    im.save(stream,format="PNG",optimize=True)
    return stream.getvalue()

def _variant_dict(v:CampaignCreative)->dict:
    scores=json.loads(v.scores_json)
    return {"id":v.id,"item_id":v.item_id,"mime":v.mime,"selected":v.selected,
            "provenance":v.provenance,"scores":scores,"prompt":v.prompt}

def _list(db:Session,cid:str,iid:str):
    records=db.scalars(select(CampaignCreative).where(CampaignCreative.campaign_id==cid,
                      CampaignCreative.item_id==iid).order_by(CampaignCreative.created_at)).all()
    data=[_variant_dict(r) for r in records]
    if data:
        best=max(data,key=lambda d:d["scores"].get("final_score") or 0)["id"]
        for d in data:d["recommended"]=d["id"]==best
    return data

@router.post("/api/v1/campaigns/{campaign_id}/items/{item_id}/creatives",status_code=201)
def generate(campaign_id:str,item_id:str,workspace_id:str,body:RequestVariants,
             user:User=Depends(current_user),db:Session=Depends(session)):
    return generate_variants(campaign_id,item_id,workspace_id,body,user,db)


def generate_variants(campaign_id,item_id,workspace_id,body,user,db,budget_run_id=None):
    campaign,item=scope(db,workspace_id,campaign_id,item_id,user)
    content=json.loads(item.item_json)
    brief=content.get("creative_brief","")
    image_prompt=body.prompt_override or content.get("image_prompt","")
    prompt=("Create a product campaign visual from the owner-reviewed image direction. Do not invent product features, readable copy, logos, or endorsements. "
            f"Business context: {campaign.business_description[:100]}. "
            f"Image prompt: {image_prompt[:1000]}. Visual guidance: {brief[:80]}. Mood: {body.brand_mood}.")
    prompt=prompt[:1500]
    from app.campaign_routes import generation_is_live
    live=generation_is_live(user,body.generation_mode)
    signature=hashlib.sha256(json.dumps({"campaign":campaign_id,"item":item_id,"body":body.model_dump(mode="json",exclude={"request_id"}),"prompt":prompt},sort_keys=True).encode()).hexdigest()
    model_run=None
    if body.request_id:
        model_run=db.get(WorkflowRun,str(body.request_id))
        if model_run:
            data=json.loads(model_run.result_json)
            if model_run.workspace_id!=workspace_id:raise HTTPException(404,"Creative request not found")
            if data.get("operation")!="campaign_creative" or data.get("signature")!=signature:raise HTTPException(409,"Request ID belongs to different creative inputs")
            if model_run.status!="inferred":raise HTTPException(409,"Creative request is pending or failed; no automatic paid retry")
            return {**data["result"],"variants":_list(db,campaign_id,item_id)}
        model_run=WorkflowRun(id=str(body.request_id),workspace_id=workspace_id,website="campaign-creative",objective=campaign.goal,status="pending",result_json=json.dumps({"operation":"campaign_creative","signature":signature}))
        db.add(model_run)
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,"Creative request already exists; no duplicate generation started") from None
    elif live:model_run=create_model_run(db,workspace_id,"user-supplied-campaign",campaign.goal)
    client=MetaClient(owner_id=user.id,workspace_id=workspace_id,run_id=budget_run_id or (model_run.id if model_run else None))
    created=[]
    problem=None
    for ix in range(body.variants):
        try:
            if live:
                result=client.image(prompt,"1024x1024")
                if result.get("provenance")!="live_meta":raise ValueError("Live creative output required")
                binary=base64.b64decode(result["data"]["b64_json"],validate=True)
                provenance="live_meta"
            else:
                binary=sample_gradient(f"{campaign_id}:{item_id}:{ix}")
                provenance="sample"
            local=measure_image(binary)
            mime={"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp"}[local["format"]]
            scores={"local":local,"brief_match":None,"final_score":None,"score_weights":None,"provenance":provenance}
            variant=CampaignCreative(campaign_id=campaign_id,item_id=item_id,prompt=prompt,
                 mime=mime,image_blob=binary,scores_json=json.dumps(scores),provenance=provenance,selected=False)
            db.add(variant);db.commit();db.refresh(variant)
            created.append(_variant_dict(variant))
            if live and body.evaluate:
                try:
                    evaluated=client.vision(binary,mime,f"Estimate visual match to this brief, no fabricated facts: {brief}",BriefMatch.model_json_schema())
                    match=BriefMatch.model_validate(evaluated["data"]).model_dump()
                    scores.update(brief_match=match,final_score=round((local["technical_readiness"]+match["brief_match"])/2),score_weights={"technical_readiness":0.5,"brief_match":0.5})
                    variant.scores_json=json.dumps(scores);db.commit()
                except Exception:
                    db.rollback();problem="Image saved. Optional visual assessment failed or reached its budget; no automatic retry."
                    break
        except Exception as exc:
            # Stop on quota/model errors, no automatic retries and keep prior successful variants.
            problem=f"Generation stopped ({type(exc).__name__}); previously created variants preserved"
            break
    items=_list(db,campaign_id,item_id)
    response={"variants":items,"created_count":len(created),"requested":body.variants,
            "partial":len(created)<body.variants,"warning":problem,
            "note":"Saved drafts only. Selection and approval are separate owner decisions."}
    if model_run:
        model_run.status="inferred" if created else "failed"
        model_run.result_json=json.dumps({"operation":"campaign_creative","signature":signature,"result":response})
        db.commit()
    return response

@router.get("/api/v1/campaigns/{campaign_id}/items/{item_id}/creatives")
def list_variants(campaign_id:str,item_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    scope(db,workspace_id,campaign_id,item_id,user)
    return _list(db,campaign_id,item_id)

def _get(db,cid,iid,vid):
    v=db.scalar(select(CampaignCreative).where(CampaignCreative.id==vid,CampaignCreative.campaign_id==cid,
                  CampaignCreative.item_id==iid))
    if v is None:raise HTTPException(404,"Creative not found")
    return v

@router.get("/api/v1/campaigns/{campaign_id}/items/{item_id}/creatives/{variant_id}/image")
def image_bytes(campaign_id:str,item_id:str,variant_id:str,workspace_id:str,
                user:User=Depends(current_user),db:Session=Depends(session)):
    scope(db,workspace_id,campaign_id,item_id,user)
    v=_get(db,campaign_id,item_id,variant_id)
    return Response(content=v.image_blob,media_type=v.mime,
        headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})

@router.post("/api/v1/campaigns/{campaign_id}/items/{item_id}/creatives/{variant_id}/select")
def select_variant(campaign_id:str,item_id:str,variant_id:str,workspace_id:str,
                   user:User=Depends(current_user),db:Session=Depends(session)):
    scope(db,workspace_id,campaign_id,item_id,user)
    variant=_get(db,campaign_id,item_id,variant_id)
    selected_ids=db.scalars(select(CampaignCreative.id).where(CampaignCreative.item_id==item_id,CampaignCreative.selected.is_(True),CampaignCreative.id!=variant_id)).all()
    if selected_ids and db.scalar(select(ApprovalRecord.id).where(ApprovalRecord.target_kind=="creative",ApprovalRecord.target_id.in_(selected_ids),ApprovalRecord.state!="proposed")):
        raise HTTPException(409,"Reopen the selected visual's review before replacing it")
    for v in db.scalars(select(CampaignCreative).where(CampaignCreative.item_id==item_id)).all():
        v.selected=(v.id==variant.id)
    db.commit()
    return {**_variant_dict(variant),"note":"Selection recorded only. No image published."}

@router.delete("/api/v1/campaigns/{campaign_id}/items/{item_id}/creatives/{variant_id}",status_code=204)
def remove(campaign_id:str,item_id:str,variant_id:str,workspace_id:str,
           user:User=Depends(current_user),db:Session=Depends(session)):
    scope(db,workspace_id,campaign_id,item_id,user)
    v=_get(db,campaign_id,item_id,variant_id)
    if v.selected:raise HTTPException(409,"Deselect before deleting a selected creative")
    if db.scalar(select(ApprovalRecord.id).where(ApprovalRecord.target_kind=="creative",ApprovalRecord.target_id==v.id,ApprovalRecord.state!="proposed")):raise HTTPException(409,"Reopen the visual review before deleting it")
    db.delete(v);db.commit()
