"""Owner-only onboarding, editable business identity, research and private assets."""
import json
import re
from datetime import timedelta
from typing import Literal
from uuid import UUID,uuid4
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException,File,Form,UploadFile,Response
from pydantic import BaseModel,Field,field_validator,model_validator
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.auth import current_user
from app.workspace_store import Workspace,User,WorkflowRun,session,utcnow
from app.workspace_routes import owned
from app.business_store import BusinessProfile,BrandResearchJob,BrandAsset
from app.business_files import validate_upload,store_asset,asset_info,MAX_FILE
from app.brand_capture import clean_url,restricted
from app.business_research import empty_report

router=APIRouter(prefix="/api/v1",tags=["Business onboarding and research"])
INDUSTRIES=["Manufacturing","Retail & ecommerce","Food & hospitality","Professional services","Construction & interiors",
    "Health & wellness","Education","Beauty & personal care","Travel & tourism","Technology","Arts & crafts","Agriculture","Real estate","Other"]
SOCIAL_HOSTS={"facebook":("facebook.com","fb.com"),"instagram":("instagram.com",),"youtube":("youtube.com","youtu.be"),
    "linkedin":("linkedin.com",),"x":("x.com","twitter.com"),"tiktok":("tiktok.com",),"pinterest":("pinterest.com",),
    "google_business":("google.com","google.co.in","maps.app.goo.gl","goo.gl"),"whatsapp":("wa.me","whatsapp.com"),"other":()}


def url_value(value):
    value=value.strip()
    if value and "://" not in value:value="https://"+value
    return clean_url(value) if value else ""


class SocialLink(BaseModel):
    platform:Literal["facebook","instagram","youtube","linkedin","x","tiktok","pinterest","google_business","whatsapp","other"]
    url:str=Field(max_length=2000)

    @model_validator(mode="after")
    def valid_url(self):
        self.url=url_value(self.url)
        if not self.url:raise ValueError("Social URL is required")
        host=(urlsplit(self.url).hostname or "").lower()
        domains=SOCIAL_HOSTS[self.platform]
        if domains and not any(host==domain or host.endswith("."+domain) for domain in domains):
            raise ValueError("Social URL must match the selected platform")
        return self


class BusinessDetails(BaseModel):
    name:str=Field(min_length=2,max_length=160)
    industry:str=Field(max_length=80)
    industry_other:str=Field(default="",max_length=100)
    description:str=Field(default="",max_length=4000)
    website:str=Field(default="",max_length=2000)
    socials:list[SocialLink]=Field(default_factory=list,max_length=12)
    address:str=Field(default="",max_length=600)
    email:str=Field(default="",max_length=255)
    phone:str=Field(default="",max_length=40)

    @field_validator("name","description","address","phone","industry_other")
    @classmethod
    def trim(cls,value):return value.strip()

    @field_validator("email")
    @classmethod
    def email_format(cls,value):
        value=value.strip()
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value):raise ValueError("Enter a valid business email")
        return value

    @model_validator(mode="after")
    def valid_business(self):
        if len(self.name)<2:raise ValueError("Business name is required")
        if self.industry not in INDUSTRIES:raise ValueError("Choose an industry or Other")
        if self.industry=="Other" and not self.industry_other:raise ValueError("Describe your industry")
        self.website=url_value(self.website)
        if self.website and restricted(self.website):raise ValueError("Add this platform under social links; website crawling is reserved for your own site")
        if len({(item.platform,item.url) for item in self.socials})!=len(self.socials):raise ValueError("Remove duplicate social links")
        return self


class SaveBusiness(BaseModel):
    workspace_id:str|None=None
    details:BusinessDetails
    consent:bool=False


class ResearchChoice(BaseModel):
    request_id:UUID
    use_ai:bool=True
    start_research:bool=False
    continue_job_id:str|None=None


def profile_info(row):
    if row is None:return None
    return {"workspace_id":row.workspace_id,"details":json.loads(row.details_json),"provenance":"user_supplied",
        "consent":bool(row.consent_at),"consent_at":row.consent_at.isoformat() if row.consent_at else None,
        "consent_version":row.consent_version,"onboarding_completed":bool(row.completed_at),"updated_at":row.updated_at.isoformat()}


def job_info(row):
    if row is None:return None
    return {"id":row.id,"state":row.state,"created_at":row.created_at.isoformat(),"updated_at":row.updated_at.isoformat(),
        "input_profile":json.loads(row.input_json)["profile"],"report":json.loads(row.report_json)}


def profile_owned(db,user,workspace_id):
    owned(db,user,workspace_id)
    return db.get(BusinessProfile,workspace_id)


@router.get("/business-profile/options")
def options(user:User=Depends(current_user)):
    return {"industries":INDUSTRIES,"social_platforms":list(SOCIAL_HOSTS),"page_limit":10,"file_limit_mb":8}


@router.post("/business-profile",status_code=201)
def save_profile(body:SaveBusiness,user:User=Depends(current_user),db:Session=Depends(session)):
    if user.is_demo:raise HTTPException(403,"Business onboarding requires an owner account")
    if body.workspace_id:
        workspace=owned(db,user,body.workspace_id)
    else:
        if (db.scalar(select(func.count()).select_from(Workspace).where(Workspace.owner_id==user.id)) or 0)>=20:
            raise HTTPException(429,"Workspace limit reached; choose an existing workspace")
        workspace=Workspace(owner_id=user.id,name=body.details.name);db.add(workspace);db.flush()
    row=db.get(BusinessProfile,workspace.id)
    if not row:row=BusinessProfile(workspace_id=workspace.id);db.add(row)
    row.details_json=body.details.model_dump_json();row.updated_at=utcnow();workspace.name=body.details.name
    if body.consent:
        if not row.consent_at:row.consent_at=utcnow()
        row.consent_version="brand-research-v1"
    else:row.consent_at=None
    db.commit();db.refresh(row)
    return profile_info(row)


@router.get("/workspaces/{workspace_id}/business-profile")
def get_profile(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    return profile_info(profile_owned(db,user,workspace_id))


def enqueue(db,user,workspace_id,body):
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    profile=profile_owned(db,user,workspace_id)
    if user.is_demo:raise HTTPException(403,"Public guest research is disabled")
    if not profile or not profile.consent_at:raise HTTPException(422,"Save business details and grant research consent first")
    previous=db.scalar(select(BrandResearchJob).where(BrandResearchJob.workspace_id==workspace_id,BrandResearchJob.request_id==str(body.request_id)))
    if previous:return previous
    active=db.scalar(select(BrandResearchJob).where(BrandResearchJob.workspace_id==workspace_id,BrandResearchJob.state.in_(["queued","running"])))
    if active:raise HTTPException(409,"Research is already queued or running; view its progress")
    count=db.scalar(select(func.count()).select_from(BrandResearchJob).where(BrandResearchJob.workspace_id==workspace_id,BrandResearchJob.created_at>utcnow()-timedelta(hours=1)))
    if count>=4:raise HTTPException(429,"Research limit: four runs per workspace per hour")
    inputs={"profile":json.loads(profile.details_json),"use_ai":body.use_ai}
    if body.continue_job_id:
        previous=db.scalar(select(BrandResearchJob).where(BrandResearchJob.id==body.continue_job_id,BrandResearchJob.workspace_id==workspace_id))
        if not previous:raise HTTPException(404,"Previous research not found")
        if json.loads(previous.input_json)["profile"].get("website")!=inputs["profile"].get("website"):
            raise HTTPException(409,"Website changed; start a new research run instead of continuing old URLs")
        remaining=json.loads(previous.report_json).get("remaining_urls",[])
        if not remaining:raise HTTPException(409,"No remaining pages are recorded")
        inputs.update(continue_urls=remaining,use_ai=False)
    job=BrandResearchJob(workspace_id=workspace_id,request_id=str(body.request_id),input_json=json.dumps(inputs),report_json=json.dumps(empty_report()))
    db.add(job);db.flush()
    db.add(WorkflowRun(id=job.id,workspace_id=workspace_id,website=inputs["profile"].get("website") or "owner-supplied-business",
        objective="Business onboarding research",status="pending",result_json=json.dumps({"operation":"brand_research","provenance":"user_supplied"})))
    db.commit();return job


@router.post("/workspaces/{workspace_id}/business-profile/complete")
def complete(workspace_id:str,body:ResearchChoice,user:User=Depends(current_user),db:Session=Depends(session)):
    profile=profile_owned(db,user,workspace_id)
    if not profile:raise HTTPException(422,"Save your business profile first")
    job=enqueue(db,user,workspace_id,body) if body.start_research else None
    profile.completed_at=profile.completed_at or utcnow();db.commit()
    return {"profile":profile_info(profile),"job":job_info(job)}


@router.post("/workspaces/{workspace_id}/business-profile/research",status_code=202)
def start_research(workspace_id:str,body:ResearchChoice,user:User=Depends(current_user),db:Session=Depends(session)):
    return job_info(enqueue(db,user,workspace_id,body))


@router.get("/workspaces/{workspace_id}/business-profile/research")
def research_status(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    rows=db.scalars(select(BrandResearchJob).where(BrandResearchJob.workspace_id==workspace_id).order_by(BrandResearchJob.created_at.desc()).limit(12)).all()
    return [job_info(row) for row in rows]


@router.get("/workspaces/{workspace_id}/business-profile/assets")
def assets(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    return [asset_info(row) for row in db.scalars(select(BrandAsset).where(BrandAsset.workspace_id==workspace_id).order_by(BrandAsset.created_at.desc()).limit(300)).all()]


@router.post("/workspaces/{workspace_id}/business-profile/assets",status_code=201)
def upload(workspace_id:str,kind:Literal["logo","document","image"]=Form("document"),consent:bool=Form(False),
    sha256:str|None=Form(None),file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(session)):
    profile=profile_owned(db,user,workspace_id)
    if user.is_demo:raise HTTPException(403,"Owner account required")
    if not consent or not profile or not profile.consent_at:raise HTTPException(422,"Consent to store these business materials is required")
    payload=file.file.read(MAX_FILE+1)
    try:
        name,mime,metadata=validate_upload(payload,file.filename or "business-file",kind)
        if kind=="image" and not mime.startswith("image/"):raise ValueError("An image file is required")
        row=store_asset(db,workspace_id,kind,name,mime,payload,metadata=metadata,supplied_hash=sha256)
        db.commit();return asset_info(row)
    except (ValueError,UnicodeError) as exc:db.rollback();raise HTTPException(422,str(exc)) from None


@router.get("/workspaces/{workspace_id}/business-profile/assets/{asset_id}")
def download_asset(workspace_id:str,asset_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    asset=db.scalar(select(BrandAsset).where(BrandAsset.id==asset_id,BrandAsset.workspace_id==workspace_id))
    if not asset:raise HTTPException(404,"Business asset not found")
    inline=asset.mime in ("image/png","image/jpeg","image/webp","image/x-icon","image/vnd.microsoft.icon")
    return Response(asset.content,media_type=asset.mime,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff",
        "Content-Disposition":("inline" if inline else "attachment")+'; filename="'+asset.filename.replace('"','_')+'"',
        "Content-Security-Policy":"default-src 'none'; sandbox"})
