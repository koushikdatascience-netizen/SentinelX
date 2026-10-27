"""Password authentication with signed bearer tokens. Never place secrets in client code."""
import hashlib
import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update, case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from app.workspace_store import LoginAttempt, User, DemoSession, session

bearer=HTTPBearer(auto_error=False)
def secret():
    value=os.getenv("JWT_SECRET","")
    if len(value)<32:
        raise HTTPException(503,"JWT_SECRET must be configured (32+ characters)")
    return value
def hash_password(password: str)->str:
    if len(password.encode())>72: raise ValueError("Password exceeds bcrypt limit")
    return bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()
def check_password(password: str, hashed: str)->bool:
    return len(password.encode())<=72 and bcrypt.checkpw(password.encode(),hashed.encode())

_DUMMY_PASSWORD_HASH=bcrypt.hashpw(b"sentinelx-invalid-password",bcrypt.gensalt()).decode()

def begin_login_attempt(db:Session,email:str)->tuple[str,int,int,datetime]:
    """Create/reset and check a shared per-account login window before bcrypt work."""
    try:
        maximum=int(os.getenv("AUTH_LOGIN_MAX_ATTEMPTS","5"))
        window=int(os.getenv("AUTH_LOGIN_WINDOW_SECONDS","900"))
        if maximum<1 or window<60: raise ValueError
    except ValueError:
        raise HTTPException(503,"Login throttling is misconfigured") from None
    email_key=hashlib.sha256(email.strip().lower().encode()).hexdigest()
    now=datetime.now(timezone.utc)
    expired=LoginAttempt.window_started_at < now-timedelta(seconds=window)
    db.execute(delete(LoginAttempt).where(
        LoginAttempt.window_started_at < now-timedelta(seconds=window*2)))
    insert=pg_insert if db.bind.dialect.name=="postgresql" else sqlite_insert
    stmt=insert(LoginAttempt).values(email_key=email_key,window_started_at=now,attempts=0,locked_until=None)
    stmt=stmt.on_conflict_do_update(index_elements=["email_key"],set_={
        "window_started_at":case((expired,now),else_=LoginAttempt.window_started_at),
        "attempts":case((expired,0),else_=LoginAttempt.attempts),
        "locked_until":case((expired,None),else_=LoginAttempt.locked_until),
    })
    db.execute(stmt)
    record=db.get(LoginAttempt,email_key)
    locked=record.locked_until
    if locked and locked.tzinfo is None: locked=locked.replace(tzinfo=timezone.utc)
    if locked and locked>now:
        retry=max(1,int((locked-now).total_seconds()))
        db.rollback()
        raise HTTPException(429,"Login temporarily unavailable",headers={"Retry-After":str(retry)})
    return email_key,maximum,window,now

def record_login_failure(db:Session,email_key:str,maximum:int,window:int,now:datetime)->None:
    next_attempt=LoginAttempt.attempts+1
    db.execute(update(LoginAttempt).where(LoginAttempt.email_key==email_key).values(
        attempts=next_attempt,
        locked_until=case((next_attempt>=maximum,now+timedelta(seconds=window)),else_=None)))
    db.commit()
    record=db.scalar(select(LoginAttempt).where(LoginAttempt.email_key==email_key).execution_options(populate_existing=True))
    if record and record.locked_until:
        locked=record.locked_until
        if locked.tzinfo is None: locked=locked.replace(tzinfo=timezone.utc)
        retry=max(1,int((locked-now).total_seconds()))
        raise HTTPException(429,"Login temporarily unavailable",headers={"Retry-After":str(retry)})

def clear_login_attempts(db:Session,email_key:str)->None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.email_key==email_key))
    db.commit()

def issue_token(user_id:str,ttl_minutes:int=480)->str:
    if not 1<=ttl_minutes<=480: raise ValueError("Token lifetime out of bounds")
    return jwt.encode({"sub":user_id,"exp":datetime.now(timezone.utc)+timedelta(minutes=ttl_minutes)},secret(),algorithm="HS256")
def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(session))->User:
    if not credentials: raise HTTPException(401,"Authentication required")
    try:
        payload=jwt.decode(credentials.credentials,secret(),algorithms=["HS256"])
        uid=payload["sub"]
    except (jwt.PyJWTError,KeyError,TypeError):
        raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,uid)
    if not user: raise HTTPException(401,"User not found")
    if user.is_demo:
        demo=db.scalar(select(DemoSession).where(DemoSession.user_id==user.id))
        if demo is None:raise HTTPException(401,"Demo session not found")
        expiry=demo.expires_at
        if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
        if expiry<=datetime.now(timezone.utc):
            raise HTTPException(401,"Demo session has expired")
    return user

def owned_run(db, user, workspace_id, run_id):
    """Resolve tenant scope before any model input is processed."""
    from app.workspace_store import Workspace, WorkflowRun
    workspace = db.get(Workspace, workspace_id)
    run = db.get(WorkflowRun, run_id)
    if not workspace or workspace.owner_id != user.id or not run or run.workspace_id != workspace_id:
        raise HTTPException(404, "Workspace/run not found")
    return run
