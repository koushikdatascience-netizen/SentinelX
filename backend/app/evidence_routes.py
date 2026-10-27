"""Authenticated evidence checks. This endpoint does not crawl or execute."""
from fastapi import APIRouter, Depends
from app.auth import current_user
from app.evidence import Recommendation, assess
router=APIRouter(prefix="/api/v1/evidence",tags=["Evidence"])

@router.post("/assess")
def assess_claim(body:Recommendation,user=Depends(current_user)):
    # A client-supplied boolean cannot establish independent collection.
    supplied = body.model_copy(update={"evidence": [
        item.model_copy(update={"collected": False}) for item in body.evidence
    ]})
    result = assess(supplied)
    result["source_type"] = "user_supplied_unverified"
    return result
