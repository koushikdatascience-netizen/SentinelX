"""Durable bounded research jobs, checkpoints and relational Business Twin facts."""
import hashlib
import json
import os
import threading
from datetime import timedelta
from sqlalchemy import select,update
from app.workspace_store import SessionLocal,Workspace,utcnow
from app.intelligence_store import ResearchJob,BusinessFact
from app.site_research import crawl


def fact_info(row):
    return {"id":row.id,"workspace_id":row.workspace_id,"kind":row.kind,"value":json.loads(row.value_json),
        "evidence":json.loads(row.evidence_json),"visibility":row.visibility,"verification":row.verification,
        "created_at":row.created_at.isoformat(),"updated_at":row.updated_at.isoformat()}


def save_fact(db,workspace_id,kind,value,evidence,visibility="public"):
    key=hashlib.sha256(json.dumps([kind,value,evidence.get("url","")],sort_keys=True).encode()).hexdigest()
    row=db.scalar(select(BusinessFact).where(BusinessFact.workspace_id==workspace_id,BusinessFact.fact_key==key))
    if row:
        prior=json.loads(row.evidence_json)
        if prior.get("reviews"):evidence["reviews"]=prior["reviews"]
        # Re-observing a source never upgrades identity verification. A changed
        # source invalidates a previous owner's confirmation until reviewed again.
        if prior.get("sha256")!=evidence.get("sha256"):row.verification="source_observed"
        row.evidence_json=json.dumps(evidence);row.updated_at=utcnow()
    else:
        row=BusinessFact(workspace_id=workspace_id,fact_key=key,kind=kind,value_json=json.dumps(value),
            evidence_json=json.dumps(evidence),visibility=visibility,verification="source_observed")
        db.add(row)
    return row


def materialize_facts(db,job,state):
    # Workspace lock serializes fact upserts with owner review and other sources.
    db.scalar(select(Workspace).where(Workspace.id==job.workspace_id).with_for_update())
    for page in state["pages"]:
        for fact in db.scalars(select(BusinessFact).where(BusinessFact.workspace_id==job.workspace_id)).all():
            prior=json.loads(fact.evidence_json)
            if prior.get("url")==page["url"] and prior.get("sha256")!=page["sha256"]:fact.verification="superseded"
        evidence={"research_id":job.id,"source_id":page["id"],"url":page["url"],"sha256":page["sha256"],
            "extracted_at":page["collected_at"],"last_verified_at":page["collected_at"],
            "method":"static_html","role":page["role"],"scope":"public_source_claim",
            "limitation":"Retrieval proves source contents, not business truth or profile ownership.","relationships":[]}
        for kind,value in [("page_title",page["title"]),("description",page["description"]),
            *(('phone',value) for value in page["contacts"]["phones"]),
            *(('email',value) for value in page["contacts"]["emails"]),
            *(('social_profile',{"platform":profile["platform"],"url":profile["url"]}) for profile in page["profiles"]),
            *(("structured_"+claim["kind"],claim["value"]) for claim in page.get("structured_claims",[]))]:
            if value:save_fact(db,job.workspace_id,kind,value,{**evidence,"method":"json_ld_extraction" if kind.startswith("structured_") else "static_html"})


def checkpoint(job_id,state,lease_token):
    with SessionLocal.begin() as db:
        row=db.get(ResearchJob,job_id,with_for_update=True)
        if not row or row.state!="running":raise InterruptedError("Job no longer running")
        current=json.loads(row.payload_json)
        if current.get("lease_token")!=lease_token:raise InterruptedError("Job lease changed")
        if current.get("cancel_requested"):raise InterruptedError("Cancellation requested")
        row.payload_json=json.dumps(state);row.updated_at=utcnow()
        materialize_facts(db,row,state)


def run_job(job_id,*,pause=None):
    from uuid import uuid4
    token=str(uuid4())
    with SessionLocal.begin() as db:
        changed=db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.state=="queued")
            .values(state="running",lease_until=utcnow()+timedelta(minutes=7),updated_at=utcnow()))
        if changed.rowcount!=1:return
        row=db.get(ResearchJob,job_id);state=json.loads(row.payload_json)
        state["lease_token"]=token;state["cancel_requested"]=False
        row.payload_json=json.dumps(state)
    def cancelled():
        with SessionLocal() as db:
            row=db.get(ResearchJob,job_id)
            return not row or row.state!="running" or json.loads(row.payload_json).get("cancel_requested",False)
    try:
        kwargs={"pause":pause} if pause else {}
        outcome=crawl(state,lambda data:checkpoint(job_id,data,token),cancelled,**kwargs)
    except InterruptedError:outcome="cancelled"
    except Exception as exc:
        outcome="failed";state["errors"].append({"reason":"Research stopped ("+type(exc).__name__+")"})
    with SessionLocal.begin() as db:
        row=db.get(ResearchJob,job_id,with_for_update=True)
        if row and row.state=="running" and json.loads(row.payload_json).get("lease_token")==token:
            if json.loads(row.payload_json).get("cancel_requested"):outcome="cancelled"
            row.state=outcome;row.payload_json=json.dumps(state);row.lease_until=None;row.updated_at=utcnow()
            materialize_facts(db,row,state)


def recover_expired(db):
    # No uncertain request is silently retried. Owner explicitly resumes the
    # last persisted checkpoint after an expired worker lease.
    db.execute(update(ResearchJob).where(ResearchJob.state=="running",ResearchJob.lease_until<utcnow())
        .values(state="paused",lease_until=None,updated_at=utcnow()))


def start_worker():
    if os.getenv("ENABLE_RESEARCH_WORKER","true").lower()!="true":return None
    stop=threading.Event()
    def loop():
        while not stop.is_set():
            try:
                with SessionLocal.begin() as db:
                    recover_expired(db)
                    job_id=db.scalar(select(ResearchJob.id).where(ResearchJob.state=="queued").order_by(ResearchJob.created_at).limit(1))
                if job_id:run_job(job_id)
                else:stop.wait(2)
            except Exception:
                # Never log source content or credentials; the persisted job
                # lease allows safe explicit recovery after a database outage.
                stop.wait(5)
    thread=threading.Thread(target=loop,name="sentinelx-research",daemon=True);thread.start()
    return stop,thread


def stop_worker(worker):
    if worker:worker[0].set();worker[1].join(timeout=1)
