"""Source-attributed, locally storable creative variants. No social publishing."""
import base64
import hashlib
import io
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw

from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import User, CampaignCreative, CampaignItem, CampaignProject, session
from app.image_scoring import measure_image
from app.meta_client import MetaClient

router=APIRouter(tags=["Creatives"])

class RequestVariants(BaseModel):
    variants: int=Field(default=2,ge=1,le=3)
    brand_mood: str=Field(default="warm, polished, natural",min_length=3,max_length=100)

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
    campaign,item=scope(db,workspace_id,campaign_id,item_id,user)
    brief=json.loads(item.item_json).get("creative_brief","")
    prompt=("Product campaign creative, no logos or invented endorsements. "
            f"Business: {campaign.business_description[:400]}. "
            f"Visual brief: {brief[:550]}. Mood: {body.brand_mood}.")
    prompt=prompt[:1500]
    live=(not user.is_demo) and MetaClient._enabled(True)
    if live:
        from app.campaign_routes import claim_attempt
        claim_attempt(db,workspace_id)
    created=[]
    problem=None
    for ix in range(body.variants):
        try:
            if live:
                result=MetaClient().image(prompt,"1024x1024")
                binary=base64.b64decode(result["data"]["image_b64"],validate=True)
                provenance="live_meta"
            else:
                binary=sample_gradient(f"{campaign_id}:{item_id}:{ix}")
                provenance="sample"
            local=measure_image(binary)
            mime={"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp"}[local["format"]]
            brief_match=None
            if live:
                evaluated=MetaClient().vision(binary,mime,
                    f"Estimate visual match to this brief, no fabricated facts: {brief}",
                    BriefMatch.model_json_schema())
                brief_match=BriefMatch.model_validate(evaluated["data"]).model_dump()
            final=(round((local["technical_readiness"]+brief_match["brief_match"])/2)
                   if brief_match else None)
            scores={"local":local,"brief_match":brief_match,"final_score":final,
                    "score_weights":{"technical_readiness":0.5,"brief_match":0.5} if final is not None else None,
                    "provenance":provenance}
            variant=CampaignCreative(campaign_id=campaign_id,item_id=item_id,prompt=prompt,
                 mime=mime,image_blob=binary,scores_json=json.dumps(scores),provenance=provenance,selected=False)
            db.add(variant);db.commit();db.refresh(variant)
            created.append(_variant_dict(variant))
        except Exception as exc:
            # Stop on quota/model errors, no automatic retries and keep prior successful variants.
            problem=f"Generation stopped ({type(exc).__name__}); previously created variants preserved"
            break
    items=_list(db,campaign_id,item_id)
    return {"variants":items,"created_count":len(created),"requested":body.variants,
            "partial":len(created)<body.variants,"warning":problem,
            "note":"Recommended is a preview suggestion only; selection requires owner action."}

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
    db.delete(v);db.commit()
