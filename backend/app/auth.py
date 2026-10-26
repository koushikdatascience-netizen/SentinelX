"""Password authentication with signed bearer tokens. Never place secrets in client code."""
import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workspace_store import User, session

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
def issue_token(user_id:str)->str:
    return jwt.encode({"sub":user_id,"exp":datetime.now(timezone.utc)+timedelta(hours=8)},secret(),algorithm="HS256")
def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(session))->User:
    if not credentials: raise HTTPException(401,"Authentication required")
    try:
        payload=jwt.decode(credentials.credentials,secret(),algorithms=["HS256"])
        uid=payload["sub"]
    except (jwt.PyJWTError,KeyError,TypeError):
        raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,uid)
    if not user: raise HTTPException(401,"User not found")
    return user
