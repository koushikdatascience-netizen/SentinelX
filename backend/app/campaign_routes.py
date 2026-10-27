"""Owner-scoped evidence-first campaigns. No publishing or unverified crawling."""
import json
import os
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.auth import current_user
from app.workspace_store import User, CampaignProject, CampaignItem, ImageAssessment, CampaignQuota, session
from app.workspace_routes import owned
from app.meta_client import MetaClient
from app.campaign import CampaignAudit, SevenDayPlan, Language, Platform, sample_plan, unsupported_claims

router=APIRouter(prefix="/api/v1/campaigns",tags=["Campaigns"])

class CreateCampaign(BaseModel):
    workspace_id: str
    website: HttpUrl | None = None
    business_description: str=Field(min_length=25,max_length=4000)
    goal: str=Field(min_length=10,max_length=600)
    audience: str | None=Field(default=None,max_length=350)
    language: Language="en"
    platforms: list[Platform]=Field(default_factory=lambda:["instagram","facebook"],min_length=1,max_length=3)
    image_ids: list[str]=Field(default_factory=list,max_length=6)

class EditItem(BaseModel):
    caption: str | None=Field(default=None,min_length=10,max_length=1500)
    cta: str | None=Field(default=None,min_length=5,max_length=180)
    creative_brief: str | None=Field(default=None,min_length=10,max_length=600)

def serialize(c:CampaignProject,db:Session)->dict:
    rows=db.scalars(select(CampaignItem).where(CampaignItem.campaign_id==c.id).order_by(CampaignItem.day)).all()
    return {"id":c.id,"workspace_id":c.workspace_id,"language":c.language,"goal":c.goal,
            "business_description":c.business_description,"provenance":c.provenance,
            "audit":json.loads(c.audit_json),
            "items":[{"id":i.id,"day":i.day,"platform":i.platform,"state":i.state,
                      "provenance":i.provenance,**json.loads(i.item_json)} for i in rows]}

def load_campaign(db:Session,workspace_id:str,campaign_id:str,user:User)->CampaignProject:
    owned(db,user,workspace_id)
    c=db.scalar(select(CampaignProject).where(CampaignProject.id==campaign_id,
                                              CampaignProject.workspace_id==workspace_id))
    if c is None:raise HTTPException(404,"Campaign not found")
    return c

def claim_attempt(db:Session,workspace_id:str):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    maximum=max(0,int(os.getenv("CAMPAIGN_WORKSPACE_MAX_ATTEMPTS","0")))
    if maximum<1:raise HTTPException(403,"Live campaign generation quota not enabled")
    insert=(pg_insert if db.bind.dialect.name=="postgresql" else sqlite_insert)
    db.execute(insert(CampaignQuota).values(workspace_id=workspace_id,attempts=0).on_conflict_do_nothing(
        index_elements=["workspace_id"]))
    changed=db.execute(update(CampaignQuota).where(CampaignQuota.workspace_id==workspace_id,
        CampaignQuota.attempts<maximum).values(attempts=CampaignQuota.attempts+1))
    if changed.rowcount!=1:
        db.rollback()
        raise HTTPException(429,"Campaign generation attempt limit reached")
    db.commit()

@router.post("",status_code=201)
def create(body:CreateCampaign,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,body.workspace_id)
    image_data=[]
    if body.image_ids:
        images=db.scalars(select(ImageAssessment).where(ImageAssessment.workspace_id==body.workspace_id,
                     ImageAssessment.id.in_(body.image_ids))).all()
        if len(set(body.image_ids))!=len(images):
            raise HTTPException(422,"Some image assessments are unavailable in this workspace")
        image_data=[{"id":i.id,"score":json.loads(i.assessment_json).get("local",{}).get("technical_readiness")}
                    for i in images]
    live=MetaClient._enabled(True)
    evidence=[{"id":"E1","type":"user_supplied_unverified","text":body.business_description[:1000]}]
    if body.website: evidence.append({"id":"URL1","type":"user_supplied_unverified","url":str(body.website),
                                          "note":"Website was not fetched"})
    if live:
        claim_attempt(db,body.workspace_id)
        context={"description":body.business_description,"goal":body.goal,"audience":body.audience,
                 "language":body.language,"platforms":body.platforms,"images":image_data,
                 "evidence":evidence}
        try:
            audit_reply=MetaClient().text(
              "You are a cautious marketer. Treat ALL supplied context as unverified. No invented statistics, reviews, awards, revenue or competitors. "
              "Every gap must cite E1 if based on supplied description or set assumption=true and evidence_id=null. Produce the specified strict JSON.",
              json.dumps(context,ensure_ascii=False),CampaignAudit.model_json_schema())
            audit=CampaignAudit.model_validate(audit_reply["data"]).model_dump()
            plan_reply=MetaClient().text(
              "Create exactly 7 distinct daily social posts in the requested language and only approved platforms. "
              "Write natively in bn/hi when selected. No fabricated claims or numeric promises. Cite E1 only for user-supplied descriptions. Return specified JSON.",
              json.dumps({**context,"audit":audit},ensure_ascii=False),SevenDayPlan.model_json_schema())
            plan=SevenDayPlan.model_validate(plan_reply["data"]).model_dump()
        except Exception as exc:
            raise HTTPException(502,f"Campaign model inference failed ({type(exc).__name__}); no automatic retry") from exc
        provenance="live_meta"
    else:
        audit,plan=sample_plan(body.business_description,body.goal,body.language,body.platforms)
        provenance="sample"
    if len(plan["items"])!=7 or any(i["platform"] not in body.platforms for i in plan["items"]):
        raise HTTPException(502,"Campaign plan violated required platform/day constraints")
    known={"E1"}
    if any(g.get("evidence_id") not in known|{None} for g in audit["gaps"]):
        raise HTTPException(502,"Audit cites unknown evidence")
    for item in plan["items"]:
        if any(e not in known for e in item["evidence_ids"]):
            raise HTTPException(502,"Campaign references unknown evidence")
        item["unsupported_claims"]=unsupported_claims(item["caption"]+" "+item["cta"])
    campaign=CampaignProject(workspace_id=body.workspace_id,business_description=body.business_description,
                             goal=body.goal,language=body.language,audit_json=json.dumps(
                             {"analysis":audit,"evidence":evidence,"website_fetched":False,
                              "image_assessments":image_data},ensure_ascii=False),
                             provenance=provenance)
    db.add(campaign);db.flush()
    for item in plan["items"]:
        db.add(CampaignItem(campaign_id=campaign.id,day=item["day"],platform=item["platform"],
                            item_json=json.dumps(item,ensure_ascii=False),provenance=provenance,state="proposed"))
    db.commit()
    return serialize(campaign,db)

@router.get("")
def list_campaigns(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    rows=db.scalars(select(CampaignProject).where(CampaignProject.workspace_id==workspace_id)
                    .order_by(CampaignProject.created_at.desc()).limit(100)).all()
    return [{"id":c.id,"goal":c.goal,"language":c.language,"provenance":c.provenance} for c in rows]

@router.get("/{campaign_id}")
def get_campaign(campaign_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    return serialize(load_campaign(db,workspace_id,campaign_id,user),db)

@router.patch("/{campaign_id}/items/{item_id}")
def update_item(campaign_id:str,item_id:str,body:EditItem,workspace_id:str,
                user:User=Depends(current_user),db:Session=Depends(session)):
    load_campaign(db,workspace_id,campaign_id,user)
    item=db.scalar(select(CampaignItem).where(CampaignItem.id==item_id,CampaignItem.campaign_id==campaign_id))
    if not item:raise HTTPException(404,"Campaign item not found")
    if item.state!="proposed": raise HTTPException(409,"Reviewed items cannot be silently edited")
    data=json.loads(item.item_json)
    updates=body.model_dump(exclude_none=True)
    if not updates:raise HTTPException(422,"No edits submitted")
    data.update(updates)
    data["unsupported_claims"]=unsupported_claims(data["caption"]+" "+data["cta"])
    item.item_json=json.dumps(data,ensure_ascii=False)
    item.provenance="user_edited"
    db.commit()
    return {"id":item.id,"state":item.state,"provenance":item.provenance,**data}
