"""Private, owner-scoped file intake with deterministic analysis and deletion."""
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile,Response
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.auth import current_user
from app.workspace_routes import owned
from app.workspace_store import User,Workspace,WorkflowRun,session
from app.intelligence_store import BusinessDataset

router=APIRouter(prefix="/api/v1/data-hub",tags=["Private business data"])
MIMES={"csv":"text/csv","xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf":"application/pdf","txt":"text/plain","json":"application/json"}
PARSER_SLOTS=threading.BoundedSemaphore(2)


class UploadLimit:
    """Bound bytes before the multipart parser writes temporary upload files."""
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or not scope.get("path","").startswith("/api/v1/data-hub") or scope.get("method")!="POST":
            return await self.app(scope,receive,send)
        size=0
        async def bounded_receive():
            nonlocal size
            message=await receive();size+=len(message.get("body",b""))
            if size>6_500_000:raise HTTPException(413,"Upload batch exceeds 6 MB")
            return message
        return await self.app(scope,bounded_receive,send)


def parse_isolated(payload,extension):
    if not PARSER_SLOTS.acquire(blocking=False):raise ValueError("File processors are busy; try again after the current upload completes")
    environment={"PYTHONUTF8":"1","PYTHONDONTWRITEBYTECODE":"1"}
    for key in ("SYSTEMROOT","WINDIR"):
        if key in os.environ:environment[key]=os.environ[key]
    try:
        result=subprocess.run([sys.executable,"-m","app.data_parser",extension],input=payload,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=False,
            cwd=Path(__file__).resolve().parents[1],env=environment)
        if result.returncode!=0 or len(result.stdout)>8_000_000:raise ValueError("Parser exceeded resource limits")
        parsed=json.loads(result.stdout)
        if not parsed.get("ok"):raise ValueError(parsed.get("error","File could not be parsed"))
        return parsed["data"]
    except subprocess.TimeoutExpired:raise ValueError("File parsing exceeded 20 seconds") from None
    finally:PARSER_SLOTS.release()


def dataset_info(row,full=False):
    data=json.loads(row.analysis_json)
    if not full:
        data={key:value for key,value in data.items() if key not in ("rows","text","pages")}
    return {"id":row.id,"filename":row.filename,"version":row.version,"sha256":row.sha256,
        "size":row.size,"mime":row.mime,"created_at":row.created_at.isoformat(),"provenance":"user_supplied",
        "visibility":"private","sent_to_ai":False,"analysis":data}


def load_dataset(db,user,workspace_id,dataset_id):
    owned(db,user,workspace_id)
    row=db.scalar(select(BusinessDataset).where(BusinessDataset.id==dataset_id,BusinessDataset.workspace_id==workspace_id))
    if not row:raise HTTPException(404,"Dataset not found")
    return row


@router.get("")
def datasets(workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    return [dataset_info(row) for row in db.scalars(select(BusinessDataset).where(BusinessDataset.workspace_id==workspace_id)
        .order_by(BusinessDataset.created_at.desc())).all()]


@router.post("",status_code=201)
def upload(workspace_id:str=Form(...),consent:bool=Form(False),files:list[UploadFile]=File(...),
           user:User=Depends(current_user),db:Session=Depends(session)):
    owned(db,user,workspace_id)
    if user.is_demo:raise HTTPException(403,"Private uploads require an owner account")
    if not consent:raise HTTPException(422,"Consent to store and locally parse these private files is required")
    if not 1<=len(files)<=5:raise HTTPException(422,"Upload between one and five files at a time")
    prepared=[];errors=[];total=0
    for file in files:
        filename=re.sub(r"[^\w .()-]","_",(file.filename or "upload").replace("\\","/").split("/")[-1])[:180]
        extension=filename.rsplit(".",1)[-1].lower()
        payload=file.file.read(2_000_001);total+=len(payload)
        if extension not in MIMES or not 0<len(payload)<=2_000_000 or total>6_000_000:
            errors.append({"filename":filename,"error":"Unsupported type or file/batch size limit exceeded"});continue
        try:analysis=parse_isolated(payload,extension)
        except ValueError as exc:
            errors.append({"filename":filename,"error":str(exc)});continue
        prepared.append((filename,extension,payload,analysis))
    # Quotas and versions are serialized, including concurrent upload batches.
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    existing=db.scalars(select(BusinessDataset).where(BusinessDataset.workspace_id==workspace_id)).all()
    saved=[]
    for filename,extension,payload,analysis in prepared:
        digest=hashlib.sha256(payload).hexdigest()
        duplicate=next((row for row in existing if row.sha256==digest and row.filename==filename),None)
        if duplicate:saved.append(dataset_info(duplicate));continue
        if len(existing)>=20 or sum(row.size for row in existing)+len(payload)>20_000_000:
            errors.append({"filename":filename,"error":"Workspace limit: 20 versions / 20 MB. Delete unneeded datasets first."});continue
        version=max((row.version for row in existing if row.filename==filename),default=0)+1
        row=BusinessDataset(workspace_id=workspace_id,filename=filename,version=version,sha256=digest,
            mime=MIMES[extension],size=len(payload),original=payload,analysis_json=json.dumps(analysis))
        db.add(row);db.flush();existing.append(row);saved.append(dataset_info(row))
    db.commit()
    return {"datasets":saved,"errors":errors,"sent_to_ai":False,"joined":False}


@router.get("/{dataset_id}")
def preview(dataset_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    result=dataset_info(load_dataset(db,user,workspace_id,dataset_id),True)
    if "rows" in result["analysis"]:result["analysis"]["rows"]=result["analysis"]["rows"][:20]
    if "text" in result["analysis"]:result["analysis"]["text"]=result["analysis"]["text"][:12000]
    return result


@router.get("/{dataset_id}/download")
def download(dataset_id:str,workspace_id:str,format:str="original",user:User=Depends(current_user),db:Session=Depends(session)):
    row=load_dataset(db,user,workspace_id,dataset_id);name=row.filename;payload=row.original
    if format=="safe_csv":
        data=json.loads(row.analysis_json)
        if data["kind"]!="table":raise HTTPException(422,"CSV export requires a tabular dataset")
        stream=io.StringIO(newline="");writer=csv.writer(stream)
        for values in [[column["name"] for column in data["columns"]],*data["rows"]]:
            writer.writerow(["'"+value if value.lstrip().startswith(("=","+","-","@")) else value for value in values])
        payload=stream.getvalue().encode("utf-8-sig");name="reviewed-data.csv"
    elif format!="original":raise HTTPException(422,"Use original or safe_csv")
    return Response(payload,media_type="application/octet-stream",headers={
        "Content-Disposition":"attachment; filename*=UTF-8''"+quote(name),"X-Content-Type-Options":"nosniff",
        "Cache-Control":"no-store","Content-Security-Policy":"default-src 'none'"})


@router.delete("/{dataset_id}")
def remove(dataset_id:str,workspace_id:str,user:User=Depends(current_user),db:Session=Depends(session)):
    row=load_dataset(db,user,workspace_id,dataset_id)
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    # Redact private evidence copied into saved local agent answers.
    for run in db.scalars(select(WorkflowRun).where(WorkflowRun.workspace_id==workspace_id)).all():
        data=json.loads(run.result_json)
        if data.get("operation")=="knowledge_answer" and dataset_id in data.get("dataset_ids",[]):
            run.result_json=json.dumps({"operation":"knowledge_answer","redacted":True,"reason":"Source dataset deleted"})
    db.delete(row);db.commit()
    return {"deleted":True,"original_and_analysis_removed":True,
        "retention":"Active data removed. Existing access-controlled operator backups expire under the backup retention policy."}
