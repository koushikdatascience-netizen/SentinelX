"""Integrated research, evidence review, local answers and execution handoffs."""
import hashlib
import html
import json
import re
from datetime import timedelta
from typing import Literal
from uuid import UUID,uuid4
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import User,Workspace,WorkflowRun,session,utcnow
from app.intelligence_store import ResearchJob,BusinessFact,BusinessDataset
from app.research_jobs import fact_info,save_fact,recover_expired
from app.site_research import canonical_url,findings
from app.data_hub import dataset_info,load_dataset

router=APIRouter(prefix="/api/v1/intelligence",tags=["Living business intelligence"])


def load_job(db,user,workspace_id,job_id,lock=False):
    owned(db,user,workspace_id)
    query=select(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.workspace_id==workspace_id)
    row=db.scalar(query.with_for_update() if lock else query)
    if not row:raise HTTPException(404,"Research not found")
    return row


def job_info(row,full=False):
    payload=json.loads(row.payload_json)
    result={"id":row.id,"workspace_id":row.workspace_id,"state":row.state,"website":payload["website"],
        "business_name":payload["business_name"],"page_count":len(payload["pages"]),"max_pages":payload["max_pages"],
        "errors":payload["errors"],"requests":payload.get("requests",0),"remaining_urls":len(payload["queue"]),
        "created_at":row.created_at.isoformat(),"updated_at":row.updated_at.isoformat(),
        "cancel_requested":payload.get("cancel_requested",False),"method":"deterministic_public_research",
        "model_calls":0,"complete_site_coverage":False}
    if full:result.update(pages=payload["pages"],coverage=payload.get("coverage",[]),limitations=payload["limitations"])
    return result


class StartResearch(BaseModel):
    workspace_id:str
    request_id:UUID=Field(default_factory=uuid4)
    website:str=Field(max_length=2000)
    business_name:str=Field(min_length=2,max_length=160)
    competitors:list[str]=Field(default_factory=list,max_length=2)
    consent_public_fetch:bool=False
    max_pages:int=Field(default=8,ge=1,le=12)
    max_depth:int=Field(default=2,ge=0,le=2)


@router.post("/research",status_code=202)
def start(body:StartResearch,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,body.workspace_id)
    if user.is_demo:raise HTTPException(403,"Public research requires an owner account")
    if not body.consent_public_fetch:raise HTTPException(422,"Consent to retrieve these public websites is required")
    urls=[canonical_url(value) for value in [body.website,*body.competitors]]
    if not all(urls):raise HTTPException(422,"Use public HTTPS URLs without query strings or credentials")
    if len({urlsplit(url).hostname for url in urls})!=len(urls):raise HTTPException(422,"Select distinct business/competitor domains")
    signature=hashlib.sha256(body.model_dump_json(exclude={"request_id"}).encode()).hexdigest()
    existing=db.get(ResearchJob,str(body.request_id))
    if existing:
        row=load_job(db,user,body.workspace_id,existing.id)
        if json.loads(row.payload_json).get("signature")!=signature:raise HTTPException(409,"Request ID belongs to different inputs")
        return job_info(row)
    db.scalar(select(Workspace).where(Workspace.id==body.workspace_id).with_for_update())
    recover_expired(db)
    active=db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.workspace_id==body.workspace_id,
        ResearchJob.state.in_(["queued","running"])))
    recent=db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.workspace_id==body.workspace_id,
        ResearchJob.created_at>=utcnow()-timedelta(days=1)))
    if active or recent>=8:raise HTTPException(429,"One active research job and eight new jobs per workspace per day are allowed")
    count=db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.workspace_id==body.workspace_id))
    if count>=40:raise HTTPException(429,"Workspace research history limit reached; operator retention review required")
    state={"signature":signature,"website":urls[0],"business_name":body.business_name,
        "max_pages":body.max_pages,"max_depth":body.max_depth,
        "queue":[[url,0,"business" if index==0 else "comparison"] for index,url in enumerate(urls)],
        "visited":[],"pages":[],"errors":[],"requests":0,"cancel_requested":False,
        "limitations":["Bounded static HTML research; JavaScript, images and videos are not interpreted by this crawl.",
            "Technical signals are observations, not measured accessibility, search rank, responsiveness or conversion scores.",
            "Social links are candidates, not verified ownership. No social posts, Maps data or private analytics were fetched.",
            "Competitor selection is supplied by the owner; relevance and real-world claims require review."]}
    row=ResearchJob(id=str(body.request_id),workspace_id=body.workspace_id,payload_json=json.dumps(state),state="queued")
    db.add(row);db.commit();return job_info(row)


@router.get("/research")
def jobs(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id);recover_expired(db);db.commit()
    return [job_info(row) for row in db.scalars(select(ResearchJob).where(ResearchJob.workspace_id==workspace_id)
        .order_by(ResearchJob.created_at.desc()).limit(40)).all()]


@router.get("/research/{job_id}")
def job(job_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    return job_info(load_job(db,user,workspace_id,job_id),True)


@router.post("/research/{job_id}/control/{operation}")
def control(job_id:str,operation:Literal["cancel","resume"],workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    recover_expired(db)
    row=load_job(db,user,workspace_id,job_id,True);data=json.loads(row.payload_json)
    if operation=="cancel":
        if row.state=="queued":row.state="cancelled"
        elif row.state=="running":data["cancel_requested"]=True
        else:raise HTTPException(409,"Only queued or running jobs can be cancelled")
    else:
        if row.state not in ("paused","cancelled"):raise HTTPException(409,"Only interrupted or cancelled jobs can resume")
        if not data["queue"] or data["requests"]>=40:raise HTTPException(409,"No resumable URLs or the request budget is exhausted")
        active=db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.workspace_id==workspace_id,ResearchJob.state.in_(["queued","running"])))
        if active:raise HTTPException(409,"Another research job is active")
        data["cancel_requested"]=False;row.state="queued"
    row.payload_json=json.dumps(data);row.updated_at=utcnow();db.commit();return job_info(row)


@router.get("/twin")
def twin(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    rows=db.scalars(select(BusinessFact).where(BusinessFact.workspace_id==workspace_id).order_by(BusinessFact.updated_at.desc()).limit(1500)).all()
    return {"facts":[fact_info(row) for row in rows],"model_calls":0,"limit":1500,
        "note":"Source observations and owner confirmations remain distinct. Missing fields are unknown, not inferred."}


class FactReview(BaseModel):
    decision:Literal["owner_confirmed","rejected","source_observed"]
    note:str=Field(min_length=5,max_length=500)


@router.post("/facts/{fact_id}/review")
def review_fact(fact_id:str,body:FactReview,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    row=db.scalar(select(BusinessFact).where(BusinessFact.id==fact_id,BusinessFact.workspace_id==workspace_id).with_for_update())
    if not row:raise HTTPException(404,"Fact not found")
    if row.verification=="superseded":raise HTTPException(409,"This evidence was superseded; review the current source")
    data=json.loads(row.evidence_json)
    event={"reviewer":user.id,"decision":body.decision,"note":body.note,"at":utcnow().isoformat()}
    data["reviews"]=[*data.get("reviews",[]),event][-20:]
    row.verification=body.decision;row.evidence_json=json.dumps(data);row.updated_at=utcnow();db.commit()
    return fact_info(row)


class Identity(BaseModel):
    name:str=Field(min_length=2,max_length=160)
    website:str=Field(max_length=2000)
    confirm:bool=False


@router.post("/identity")
def identity(body:Identity,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    url=canonical_url(body.website)
    if not body.confirm or not url:raise HTTPException(422,"Confirm the business name and public HTTPS website")
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    for row in db.scalars(select(BusinessFact).where(BusinessFact.workspace_id==workspace_id,BusinessFact.kind=="business_identity")):
        row.verification="superseded"
    evidence={"method":"owner_confirmation","url":url,"reviewer":user.id,"last_verified_at":utcnow().isoformat(),"scope":"user_supplied"}
    row=save_fact(db,workspace_id,"business_identity",{"name":body.name,"website":url},evidence,"user_supplied")
    row.verification="owner_confirmed";db.commit();return fact_info(row)


@router.get("/competitor-candidates")
def candidates(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id);items=[];seen=set()
    for row in db.scalars(select(WorkflowRun).where(WorkflowRun.workspace_id==workspace_id).order_by(WorkflowRun.created_at.desc()).limit(300)):
        data=json.loads(row.result_json)
        if data.get("operation")!="search_evidence" or data.get("validation_status")!="validated":continue
        for item in data.get("data",{}).get("citations",[]):
            url=canonical_url(item.get("url",""))
            if not url or url in seen:continue
            seen.add(url);items.append({"url":url,"title":item.get("title","Candidate"),"source_id":row.id,
                "captured_at":data.get("captured_at"),"classification":"unreviewed_candidate",
                "note":"Search relevance is not proof of direct competition. Select only businesses you want compared."})
    return items[:20]


@router.get("/integrations")
def integrations(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    return [{"provider":name,"state":"unsupported","implemented":False,"reason":reason} for name,reason in [
        ("Maps and local reputation","No approved Maps data adapter or account authorization is configured. No ratings or reviews collected."),
        ("Google Sheets / Drive / GA4","Product OAuth connection and token lifecycle are not implemented. Use explicitly selected file exports in Data Hub."),
        ("Social account insights","Website-linked profile discovery is available; private insights and publishing need an authorized platform adapter."),
        ("MCP services","Arbitrary MCP hosts and commands are disabled. A reviewed tool registry and credential flow remain to be implemented.")]]


@router.get("/report/{job_id}")
def report(job_id:str,workspace_id:str,format:Literal["json","html"]="json",user:User=Depends(current_user),db:Session=Depends(session)):
    row=load_job(db,user,workspace_id,job_id);data=job_info(row,True)
    data["findings"]=[finding for page in data["pages"] for finding in findings(page)]
    data["facts"]=twin(workspace_id,user,db)["facts"]
    data["datasets"]=[dataset_info(dataset) for dataset in db.scalars(select(BusinessDataset).where(BusinessDataset.workspace_id==workspace_id)).all()]
    data["comparison"]=[{"url":page["url"],"role":page["role"],"title":page["title"],"description":page["description"],
        "source_id":page["id"],"signals":page["signals"],"social_candidates":len(page["profiles"]),
        "pricing":"Unknown; not extracted","reputation":"Unknown; no provider data","private_performance":"Unavailable"} for page in data["pages"]]
    data["integrations"]=integrations(workspace_id,user,db)
    data["summary"]={"retrieved_pages":len(data["pages"]),"technical_findings":len(data["findings"]),
        "private_datasets":len(data["datasets"]),"social_candidates":sum(len(page["profiles"]) for page in data["pages"]),
        "measured_business_outcomes":None,"status":"Partial evidence coverage; review unknowns and retrieval errors"}
    if format=="json":return data
    escape=html.escape
    sections=["<!doctype html><html lang='en'><meta charset='utf-8'><title>SentinelX intelligence report</title>",
        "<style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:20px}section{border-top:1px solid #ccc;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{overflow-wrap:anywhere}</style>",
        "<h1>"+escape(data["business_name"])+" — Intelligence report</h1><p>Deterministic public evidence and private file metadata. No AI call or measured business uplift.</p>",
        "<nav><a href='#pages'>Website</a> · <a href='#facts'>Business Twin</a> · <a href='#comparison'>Competitors</a> · <a href='#data'>Data Hub</a></nav>"]
    for anchor,title,value in [("summary","Executive summary",data["summary"]),("facts","Business identity and social evidence",data["facts"]),
        ("pages","Page audit and SEO observations",data["findings"]),("comparison","Competitor comparison",data["comparison"]),
        ("data","Private data quality",data["datasets"]),("coverage","Coverage and unknowns",{key:data[key] for key in ("errors","limitations","integrations")})]:
        sections.append("<section id='"+anchor+"'><h2>"+title+"</h2><pre>"+escape(json.dumps(value,ensure_ascii=False,indent=2))+"</pre></section>")
    sections.append("</html>")
    return Response("".join(sections),media_type="text/html",headers={"Content-Disposition":"attachment; filename=sentinelx-intelligence.html",
        "Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'","X-Content-Type-Options":"nosniff","Cache-Control":"no-store"})


class AskEvidence(BaseModel):
    question:str=Field(min_length=4,max_length=600)
    job_id:str|None=None
    dataset_ids:list[str]=Field(default_factory=list,max_length=3)


@router.post("/ask")
def ask(body:AskEvidence,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id);evidence=[];trace=[]
    words=set(re.findall(r"[\w]{3,}",body.question.lower()))-{"what","does","this","that","with","have","business","show","please"}
    if body.job_id:
        row=load_job(db,user,workspace_id,body.job_id);data=json.loads(row.payload_json)
        for page in data["pages"]:
            for text in [page["description"],*re.split(r"(?<=[.!?])\s+",page["text"])]:
                if not text:continue
                score=sum(word in text.lower() for word in words)
                if score:evidence.append({"source_id":page["id"],"source_url":page["url"],"quote":text[:900],"score":score,"visibility":"public_source_claim"})
            for finding in findings(page):
                text=finding["finding"]+": "+finding["why"]+" Suggested review: "+finding["recommended_action"]
                if any(word in text.lower() for word in words):evidence.append({"source_id":page["id"],"source_url":page["url"],"quote":text,"score":2,"visibility":"deterministic_html_observation"})
        trace.append({"tool":"read_owned_research","state":"completed","sources":len(data["pages"])})
    for dataset_id in body.dataset_ids:
        dataset=load_dataset(db,user,workspace_id,dataset_id);analysis=json.loads(dataset.analysis_json)
        if analysis["kind"]=="table":
            text=json.dumps({"filename":dataset.filename,"row_count":analysis["row_count"],"duplicate_rows":analysis["duplicate_rows"],"columns":analysis["columns"]},ensure_ascii=False)
        else:text=analysis["text"][:3000]
        evidence.append({"source_id":dataset.id,"source_url":None,"quote":text,"score":10,"visibility":"private_user_supplied"})
        trace.append({"tool":"read_selected_dataset_summary","state":"completed","dataset_id":dataset.id})
    evidence.sort(key=lambda item:item["score"],reverse=True);evidence=evidence[:6]
    result={"operation":"knowledge_answer","question":body.question,"dataset_ids":body.dataset_ids,"evidence":evidence,
        "answer":"Relevant saved evidence is shown below. Review source claims and units before acting." if evidence else "No matching evidence was found in the selected research and datasets.",
        "method":"deterministic_retrieval","provenance":"user_supplied","model_calls":0,"external_actions":0,"trace":trace,
        "limitation":"Evidence lookup and computed dataset summaries, not a general reasoning or external tool-execution agent. Requests to create/publish require the separate action engine."}
    count=db.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.workspace_id==workspace_id,WorkflowRun.website=="local-knowledge-answer"))
    if count>=100:raise HTTPException(429,"Saved evidence-answer limit reached")
    row=WorkflowRun(workspace_id=workspace_id,website="local-knowledge-answer",objective=body.question,status="completed",result_json=json.dumps(result))
    db.add(row);db.commit();return {"id":row.id,**result}


@router.post("/research/{job_id}/prepare-context")
def prepare_context(job_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    row=load_job(db,user,workspace_id,job_id);data=json.loads(row.payload_json)
    if row.state not in ("completed","paused") or not data["pages"]:raise HTTPException(409,"Collect and review research evidence first")
    for existing in db.scalars(select(WorkflowRun).where(WorkflowRun.workspace_id==workspace_id,WorkflowRun.website=="public-research-context")):
        previous=json.loads(existing.result_json)
        if previous.get("research_id")==job_id:return {"id":existing.id,"website":data["website"],"reused":True}
    text="Public research observations; website claims remain unverified.\n"
    for page in data["pages"]:
        if page["role"]!="business":continue
        text+=page["title"]+" "+page["url"]+"\n"+page["text"][:500]+"\n"
        for finding in findings(page)[:2]:text+=finding["finding"]+": "+finding["recommended_action"]+"\n"
    result={"operation":"business_context","kind":"business_twin","research_id":job_id,"filename":"Public website research",
        "provenance":"user_supplied","input_provenance":"retrieved_public_page","text":text[:5000],"owner_notes":"Owner-selected collected public evidence",
        "sha256":None,"limitation":"Deterministic public HTML observations, not model inference or verified business truth. No private uploaded data included."}
    context=WorkflowRun(workspace_id=workspace_id,website="public-research-context",objective="Review research in the existing action engine",status="completed",result_json=json.dumps(result))
    db.add(context);db.commit();return {"id":context.id,"website":data["website"],"reused":False}
