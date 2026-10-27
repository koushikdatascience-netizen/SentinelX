"""Authenticated evidence checks. This endpoint does not crawl or execute."""
from fastapi import APIRouter, Depends
from app.auth import current_user
from app.evidence import Recommendation, assess
router=APIRouter(prefix="/api/v1/evidence",tags=["Evidence"])

@router.post("/assess")
def assess_claim(body:Recommendation,user=Depends(current_user)):
    return assess(body)
