"""Scoped, HTML-safe campaign landing pages and consented lead intake."""
import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import CampaignProject, CampaignCreative, LandingPage, LandingLead, User, session
from app.landing import LandingSpec, SECURITY_HEADERS, render_landing, sample_landing
from app.meta_client import MetaClient
from app.campaign import unsupported_claims

router=APIRouter(tags=["Landing pages"])

class CreateLanding(BaseModel):
    workspace_id: str
    campaign_id: str
    business_name: str=Field(min_length=2,max_length=100)
    theme: str=Field(default="modern",pattern="^(modern|warm|bold)$")
    whatsapp_number: str | None=None
    hero_image_variant_id: str | None=None

class UpdateLanding(BaseModel):
    spec: LandingSpec | None=None
    published: bool | None=None

def _owned_page(db:Session,workspace_id:str,page_id:str,user:User)->LandingPage:
    owned(db,user,workspace_id)
    page=db.scalar(select(LandingPage).join(CampaignProject,LandingPage.campaign_id==CampaignProject.id)
       .where(LandingPage.id==page_id,CampaignProject.workspace_id==workspace_id))
    if page is None:raise HTTPException(404,"Landing page not found")
    return page

def hero_image_for_page(db:Session,page:LandingPage,spec:LandingSpec)->str|None:
    vid=spec.hero_image_variant_id
    if not vid:return None
    variant=db.scalar(select(CampaignCreative).where(CampaignCreative.id==vid,
        CampaignCreative.campaign_id==page.campaign_id,CampaignCreative.selected.is_(True)))
    if variant is None:return None
    if len(variant.image_blob)>5_000_000:return None
    return "data:"+variant.mime+";base64,"+base64.b64encode(variant.image_blob).decode("ascii")

def _info(db:Session,page:LandingPage)->dict:
    leads=db.scalar(select(func.count()).select_from(LandingLead).where(LandingLead.page_id==page.id)) or 0
    return {"id":page.id,"campaign_id":page.campaign_id,"published":page.published,
            "slug":page.slug,"url":"/p/"+page.slug,"provenance":page.provenance,
            "spec":json.loads(page.spec_json),"leads_count":leads}

@router.post("/api/v1/landing/generate",status_code=201)
def generate(body:CreateLanding,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,body.workspace_id)
    campaign=db.scalar(select(CampaignProject).where(CampaignProject.id==body.campaign_id,
                    CampaignProject.workspace_id==body.workspace_id))
    if campaign is None:raise HTTPException(404,"Campaign not found")
    live=MetaClient._enabled(True)
    if live:
        # MetaClient reserves the global provider budget before the request.
        # This route requires the same workspace campaign attempt quota as campaigns.
        from app.campaign_routes import claim_attempt
        claim_attempt(db,body.workspace_id)
        try:
            result=MetaClient().text(
                "Create a useful conversion-oriented landing page without invented statistics, testimonials, awards, prices or third-party claims. "
                "Use the owner's description as unverified context only. Output strictly the specified JSON.",
                json.dumps({"description":campaign.business_description,"goal":campaign.goal,
                            "language":campaign.language,"business_name":body.business_name},ensure_ascii=False),
                LandingSpec.model_json_schema())
            spec=LandingSpec.model_validate(result["data"])
        except Exception as exc:
            raise HTTPException(502,f"Landing generation failed ({type(exc).__name__}); no automatic retry") from exc
        provenance="live_meta"
    else:
        spec=LandingSpec.model_validate(sample_landing(body.business_name,campaign.goal,campaign.language))
        provenance="sample"
    content=spec.model_dump()
    content["theme"]=body.theme
    if body.whatsapp_number:
        content["whatsapp_number"]=body.whatsapp_number
    if body.hero_image_variant_id:
        candidate=db.scalar(select(CampaignCreative).where(CampaignCreative.id==body.hero_image_variant_id,
            CampaignCreative.campaign_id==campaign.id,CampaignCreative.selected.is_(True)))
        if candidate is None:raise HTTPException(422,"Hero image must be a selected creative in this campaign")
        content["hero_image_variant_id"]=body.hero_image_variant_id
    else:
        content["hero_image_variant_id"]=None
    try: spec=LandingSpec.model_validate(content)
    except ValueError as exc:raise HTTPException(422,"Landing configuration invalid") from exc
    claims=unsupported_claims(" ".join([spec.headline,spec.offer,spec.subheadline]+spec.trust_points))
    if claims:raise HTTPException(422,"Landing contains unsupported promotional claims")
    page=LandingPage(campaign_id=campaign.id,slug=secrets.token_urlsafe(24),
                     spec_json=spec.model_dump_json(),provenance=provenance,published=False)
    db.add(page);db.commit();db.refresh(page)
    return _info(db,page)

@router.get("/api/v1/landing")
def list_pages(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    rows=db.scalars(select(LandingPage).join(CampaignProject,LandingPage.campaign_id==CampaignProject.id)
        .where(CampaignProject.workspace_id==workspace_id).order_by(LandingPage.created_at.desc()).limit(100)).all()
    return [_info(db,p) for p in rows]

@router.get("/api/v1/landing/{page_id}")
def get_page(page_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    return _info(db,_owned_page(db,workspace_id,page_id,user))

@router.patch("/api/v1/landing/{page_id}")
def update_page(page_id:str,workspace_id:str,body:UpdateLanding,
                user:User=Depends(current_user),db:Session=Depends(session)):
    page=_owned_page(db,workspace_id,page_id,user)
    if body.spec is not None:
        if body.spec.hero_image_variant_id:
            candidate=db.scalar(select(CampaignCreative).where(CampaignCreative.id==body.spec.hero_image_variant_id,
                CampaignCreative.campaign_id==page.campaign_id,CampaignCreative.selected.is_(True)))
            if candidate is None:raise HTTPException(422,"Hero image is not a selected creative")
        if page.approval_state!="proposed":
            raise HTTPException(409,"Reopen reviewed landing page before editing")
        if unsupported_claims(" ".join([body.spec.headline,body.spec.offer,body.spec.subheadline]+body.spec.trust_points)):
            raise HTTPException(422,"Landing contains unsupported promotional claims")
        page.spec_json=body.spec.model_dump_json()
        page.provenance="user_edited"
        # Material changes require a new publishing decision.
        page.published=False
    if body.published is not None:
        # Owner publishes a self-hosted page only after explicit audited approval.
        if body.published and page.approval_state!="approved":
            raise HTTPException(409,"Approve landing page before publishing")
        page.published=body.published
    db.commit()
    return _info(db,page)

@router.get("/api/v1/landing/{page_id}/preview")
def preview(page_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    p=_owned_page(db,workspace_id,page_id,user)
    spec=LandingSpec.model_validate_json(p.spec_json)
    return HTMLResponse(render_landing(spec,p.slug,p.provenance,hero_image_for_page(db,p,spec)),
                        headers=SECURITY_HEADERS)

@router.get("/api/v1/landing/{page_id}/export")
def export(page_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    p=_owned_page(db,workspace_id,page_id,user)
    spec=LandingSpec.model_validate_json(p.spec_json)
    html=render_landing(spec,p.slug,p.provenance,hero_image_for_page(db,p,spec))
    return Response(content=html,media_type="text/html",headers={
       **SECURITY_HEADERS,"Content-Disposition":f'attachment; filename="sentinelx-{p.id}.html"'})

@router.get("/p/{slug}")
def published_page(slug:str,db:Session=Depends(session)):
    p=db.scalar(select(LandingPage).where(LandingPage.slug==slug,LandingPage.published.is_(True)))
    if p is None:raise HTTPException(404,"Page not published")
    spec=LandingSpec.model_validate_json(p.spec_json)
    return HTMLResponse(render_landing(spec,p.slug,p.provenance,hero_image_for_page(db,p,spec)),
                        headers=SECURITY_HEADERS)

@router.post("/p/{slug}/lead")
def submit_lead(slug:str,request:Request,name:str=Form(...,max_length=100),phone:str=Form(...,max_length=30),
                message:str=Form(...,max_length=1500),consent:str=Form(""),db:Session=Depends(session)):
    p=db.scalar(select(LandingPage).where(LandingPage.slug==slug,LandingPage.published.is_(True)))
    if p is None:raise HTTPException(404,"Page not published")
    if consent!="yes":raise HTTPException(422,"Consent is required")
    if len(name.strip())<2 or len(message.strip())<3 or not (8<=len(phone.strip())<=30):
        raise HTTPException(422,"Invalid inquiry")
    # Do not trust client-supplied forwarding headers for rate limiting.
    ip=(request.client.host if request.client else "unknown")
    pepper=os.getenv("LEAD_IP_HASH_SECRET") or os.getenv("JWT_SECRET")
    if not pepper:raise HTTPException(503,"Lead intake is not configured")
    ip_hash=hashlib.sha256((pepper+":"+ip).encode()).hexdigest()
    cutoff=datetime.now(timezone.utc)-timedelta(hours=1)
    per_ip=db.scalar(select(func.count()).select_from(LandingLead).where(
        LandingLead.page_id==p.id,LandingLead.ip_hash==ip_hash,LandingLead.created_at>=cutoff)) or 0
    per_page=db.scalar(select(func.count()).select_from(LandingLead).where(
        LandingLead.page_id==p.id,LandingLead.created_at>=cutoff)) or 0
    if per_ip>=4 or per_page>=20:raise HTTPException(429,"Inquiry rate limit reached")
    db.add(LandingLead(page_id=p.id,name=name.strip(),phone=phone.strip(),message=message.strip(),ip_hash=ip_hash))
    db.commit()
    return HTMLResponse("<!doctype html><html><meta charset='utf-8'><title>Message received</title><body><main><h1>Message received</h1><p>Your information was submitted to the business.</p></main></body></html>",
                        headers=SECURITY_HEADERS)

@router.get("/api/v1/landing/{page_id}/leads")
def list_leads(page_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    p=_owned_page(db,workspace_id,page_id,user)
    rows=db.scalars(select(LandingLead).where(LandingLead.page_id==p.id)
                    .order_by(LandingLead.created_at.desc()).limit(200)).all()
    return [{"id":r.id,"name":r.name,"phone":r.phone,"message":r.message,
             "created_at":r.created_at.isoformat()} for r in rows]

@router.delete("/api/v1/landing/{page_id}/leads/{lead_id}",status_code=204)
def remove_lead(page_id:str,lead_id:str,workspace_id:str,
                user:User=Depends(current_user),db:Session=Depends(session)):
    p=_owned_page(db,workspace_id,page_id,user)
    lead=db.scalar(select(LandingLead).where(LandingLead.id==lead_id,LandingLead.page_id==p.id))
    if lead is None:raise HTTPException(404,"Lead not found")
    db.delete(lead);db.commit()
