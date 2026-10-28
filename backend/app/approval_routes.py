"""Append-only review decisions and zip exports; never publishes external accounts."""
import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import (
    User, CampaignProject, CampaignItem, CampaignCreative, LandingPage, ApprovalRecord, ApprovalEvent, session, utcnow
)
from app.landing import LandingSpec, render_landing
from app.landing_routes import hero_image_for_page

router=APIRouter(tags=["Approvals"])

class ReviewInput(BaseModel):
    decision: str=Field(pattern="^(approved|rejected|reopen)$")
    note: str=Field(default="",max_length=500)

def authorized_campaign(db:Session,cid:str,wid:str,user:User):
    owned(db,user,wid)
    campaign=db.scalar(select(CampaignProject).where(CampaignProject.id==cid,CampaignProject.workspace_id==wid))
    if campaign is None:raise HTTPException(404,"Campaign not found")
    return campaign

def ensure_board(db:Session,cid:str,wid:str):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sq_insert
    insert=(pg_insert if db.bind.dialect.name=="postgresql" else sq_insert)
    expected=[("campaign_item",i.id) for i in db.scalars(
        select(CampaignItem).where(CampaignItem.campaign_id==cid)).all()]
    expected += [("landing",p.id) for p in db.scalars(
        select(LandingPage).where(LandingPage.campaign_id==cid)).all()]
    expected += [("creative",v.id) for v in db.scalars(
        select(CampaignCreative).where(CampaignCreative.campaign_id==cid,CampaignCreative.selected.is_(True))).all()]
    for kind,target in expected:
        db.execute(insert(ApprovalRecord).values(workspace_id=wid,campaign_id=cid,
            target_kind=kind,target_id=target,state="proposed",created_at=utcnow()
            ).on_conflict_do_nothing(index_elements=["target_kind","target_id"]))
    db.commit()

def review_preview(db:Session,record:ApprovalRecord)->dict:
    if record.target_kind=="campaign_item":
        item=db.get(CampaignItem,record.target_id)
        if item and item.campaign_id==record.campaign_id:
            data=json.loads(item.item_json)
            return {"title":f"Day {item.day} · {data.get('platform','Post')}","description":data.get("caption","")[:400]}
    if record.target_kind=="landing":
        page=db.get(LandingPage,record.target_id)
        if page and page.campaign_id==record.campaign_id:
            data=json.loads(page.spec_json)
            return {"title":data.get("headline","Landing page"),"description":data.get("offer","")[:400]}
    if record.target_kind=="creative":
        creative=db.get(CampaignCreative,record.target_id)
        if creative and creative.campaign_id==record.campaign_id:
            return {"title":"Selected campaign visual","description":creative.prompt[:400]}
    return {"title":"Unavailable artifact","description":"Refresh the campaign before reviewing."}

@router.get("/api/v1/campaigns/{campaign_id}/board")
def campaign_board(campaign_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    authorized_campaign(db,campaign_id,workspace_id,user)
    ensure_board(db,campaign_id,workspace_id)
    records=db.scalars(select(ApprovalRecord).where(ApprovalRecord.campaign_id==campaign_id)
                      .order_by(ApprovalRecord.created_at)).all()
    return [{"id":r.id,"target_kind":r.target_kind,"target_id":r.target_id,**review_preview(db,r),
             "state":r.state,"evidence_source":"user_supplied_unverified",
             "events":[{"decision":e.decision,"note":e.note,"reviewer_id":e.reviewer_id,
                        "at":e.created_at.isoformat()} for e in db.scalars(select(ApprovalEvent)
                        .where(ApprovalEvent.approval_id==r.id).order_by(ApprovalEvent.created_at)).all()]}
            for r in records]

@router.post("/api/v1/approvals/{approval_id}/decide")
def decide(approval_id:str,workspace_id:str,body:ReviewInput,
           user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    record=db.scalar(select(ApprovalRecord).where(ApprovalRecord.id==approval_id,
                                                 ApprovalRecord.workspace_id==workspace_id)
                     .with_for_update())
    if record is None:raise HTTPException(404,"Approval not found")
    if body.decision=="reopen":
        if record.state=="proposed":raise HTTPException(409,"Already proposed")
        next_state="proposed"
    else:
        if record.state!="proposed":raise HTTPException(409,"Reviewed decisions require an explicit reopen")
        next_state=body.decision
    record.state=next_state
    if record.target_kind=="campaign_item":
        item=db.get(CampaignItem,record.target_id)
        if item is None or item.campaign_id!=record.campaign_id:raise HTTPException(404,"Campaign item missing")
        item.state=next_state
    elif record.target_kind=="creative":
        creative=db.get(CampaignCreative,record.target_id)
        if creative is None or creative.campaign_id!=record.campaign_id or not creative.selected:
            raise HTTPException(409,"Creative must be selected before approval")
    elif record.target_kind=="landing":
        page=db.get(LandingPage,record.target_id)
        if page is None or page.campaign_id!=record.campaign_id:raise HTTPException(404,"Landing missing")
        page.approval_state=next_state
        if next_state!="approved":page.published=False
    else:raise HTTPException(422,"Unsupported approval artifact")
    event=ApprovalEvent(approval_id=record.id,reviewer_id=user.id,decision=body.decision,note=body.note)
    db.add(event);db.commit()
    return {"id":record.id,"state":record.state,"decision":body.decision,
            "reviewer_id":user.id,"executed":False,"note":"Decision recorded; no external publishing action."}

@router.get("/api/v1/campaigns/{campaign_id}/export")
def export_campaign(campaign_id:str,workspace_id:str,format:str="zip",
                    user:User=Depends(current_user),db:Session=Depends(session)):
    campaign=authorized_campaign(db,campaign_id,workspace_id,user)
    if format!="zip":raise HTTPException(422,"Only ZIP export is implemented")
    # Export only approved items; labels preserve sample vs live provenance.
    items=db.scalars(select(CampaignItem).where(CampaignItem.campaign_id==campaign.id,
                   CampaignItem.state=="approved").order_by(CampaignItem.day)).all()
    pages=db.scalars(select(LandingPage).where(LandingPage.campaign_id==campaign.id,
                   LandingPage.approval_state=="approved")).all()
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as z:
        readme=[
            "SentinelX — Approved Campaign Pack",
            "All outputs require owner verification. Nothing was automatically published.",
            f"Campaign provenance: {campaign.provenance}",
            f"Business goal: {campaign.goal}",
            "Sample-labeled materials are examples, not verified model outputs or business claims.",
            "All evidence is owner-supplied unless independently verified.",
            "",
            "Included approved items:"
        ]
        for item in items:
            payload=json.loads(item.item_json)
            readme.append(f"Day {item.day}: {item.platform}, state=approved, provenance={item.provenance}")
            data=(f"Day {item.day} | {item.platform}\nProvenance: {item.provenance}\n"
                f"Caption: {payload['caption']}\nHashtags: {' '.join(payload['hashtags'])}\n"
                f"CTA: {payload['cta']}\nCreative brief: {payload['creative_brief']}\n"
                f"Evidence IDs: {', '.join(payload['evidence_ids'])}\n"
                f"Unsupported claim flags: {payload.get('unsupported_claims',[])}\n")
            z.writestr(f"posts/day-{item.day:02d}.txt",data)
        for page in pages:
            spec=LandingSpec.model_validate_json(page.spec_json)
            html=render_landing(spec,page.slug,page.provenance,hero_image_for_page(db,page,spec))
            z.writestr(f"landing/{page.id}.html",html)
            readme.append(f"Approved landing: {page.id}, provenance={page.provenance}")
        approved_creative_ids=db.scalars(select(ApprovalRecord.target_id).where(
            ApprovalRecord.campaign_id==campaign.id,ApprovalRecord.target_kind=="creative",
            ApprovalRecord.state=="approved")).all()
        for v in db.scalars(select(CampaignCreative).where(CampaignCreative.id.in_(approved_creative_ids),
                     CampaignCreative.selected.is_(True))).all():
            ext={"image/png":"png","image/jpeg":"jpg","image/webp":"webp"}.get(v.mime,"bin")
            z.writestr(f"creatives/{v.id}.{ext}",v.image_blob)
            readme.append(f"Approved creative: {v.id}, provenance={v.provenance}")
        if not items and not pages and not approved_creative_ids:
            readme.append("None. No unapproved artifacts included.")
        z.writestr("README.txt","\n".join(readme))
        z.writestr("evidence.json",json.dumps(json.loads(campaign.audit_json).get("evidence",[]),indent=2))
    return Response(content=output.getvalue(),media_type="application/zip",
                    headers={"Content-Disposition":f'attachment; filename="sentinelx-{campaign.id}.zip"'})
