"""Anonymous guest demo: bounded, database-isolated sample-only workspace."""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.auth import issue_token, hash_password
from app.workspace_store import User, Workspace, CampaignProject, CampaignItem, LandingPage, DemoSession, session
from app.campaign import sample_plan
from app.landing import sample_landing, LandingSpec

router=APIRouter(prefix="/api/v1/demo",tags=["Demo"])

@router.post("/session",status_code=201)
def create_demo_session(request:Request,db:Session=Depends(session)):
    if os.getenv("ENABLE_PUBLIC_DEMO_SESSION","false")!="true":
        raise HTTPException(403,"Guest demo sessions disabled by the operator")
    pepper=os.getenv("JWT_SECRET","")
    if len(pepper)<32:raise HTTPException(503,"JWT_SECRET not configured")
    ip=request.client.host if request.client else "unknown"
    digest=hashlib.sha256((pepper+":"+ip).encode()).hexdigest()
    cutoff=datetime.now(timezone.utc)-timedelta(hours=1)
    recent=db.scalar(select(func.count()).select_from(DemoSession).where(
        DemoSession.ip_hash==digest,DemoSession.created_at>=cutoff)) or 0
    maximum=min(5,max(1,int(os.getenv("DEMO_SESSIONS_PER_IP_HOUR","3"))))
    if recent>=maximum:raise HTTPException(429,"Guest session limit reached")
    sid=secrets.token_urlsafe(12)
    identity="guest-"+sid+"@demo.sentinelx.invalid"
    # No known password; guest receives only a short-lived bearer token.
    user=User(email=identity,password_hash=hash_password(secrets.token_urlsafe(36)),is_demo=True)
    db.add(user);db.flush()
    ws=Workspace(owner_id=user.id,name="Sample Woodworking Studio")
    db.add(ws);db.flush()
    source=("This is a fictional woodworking business demonstrating custom furniture and cabinetry. "
            "Consultations may be requested; capabilities, prices, reviews and lead times are not verified.")
    goal="Improve qualified customer inquiries using clear, evidence-aware marketing."
    audit,plan=sample_plan(source,goal,"en",["instagram","facebook"])
    campaign=CampaignProject(workspace_id=ws.id,business_description=source,goal=goal,
         language="en",audit_json=json.dumps({"analysis":audit,"evidence":[{"id":"E1",
         "type":"fictional_sample","text":source}],"website_fetched":False}),
         provenance="sample")
    db.add(campaign);db.flush()
    for row in plan["items"]:
        db.add(CampaignItem(campaign_id=campaign.id,day=row["day"],platform=row["platform"],
            item_json=json.dumps(row),provenance="sample",state="proposed"))
    landing=LandingPage(campaign_id=campaign.id,slug=secrets.token_urlsafe(24),
                        spec_json=LandingSpec.model_validate(sample_landing("Sample Woodworking Studio",goal)).model_dump_json(),
                        provenance="sample",published=False,approval_state="proposed")
    db.add(landing)
    expires=datetime.now(timezone.utc)+timedelta(minutes=20)
    db.add(DemoSession(user_id=user.id,ip_hash=digest,expires_at=expires))
    db.commit()
    return {"access_token":issue_token(user.id,ttl_minutes=20),"token_type":"bearer",
            "expires_at":expires.isoformat(),"workspace":{"id":ws.id,"name":ws.name},
            "campaign_id":campaign.id,"landing_id":landing.id,
            "provenance":"sample","paid_calls":0,
            "note":"Fictional isolated sample workspace, 20-minute access, no paid inference."}
