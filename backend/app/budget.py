"""Application-side prepaid reservation guard for text inference.

This is not an account-level financial guarantee: other keys/apps bypass it.
Only single-request text inference is covered. Default paid calls disabled.
"""
import os
from sqlalchemy import Integer, String, update, select
from sqlalchemy.orm import Mapped, mapped_column
from app.workspace_store import Base, SessionLocal

class ApiBudget(Base):
    __tablename__="api_budgets"
    provider: Mapped[str]=mapped_column(String(40),primary_key=True)
    reserved_cents: Mapped[int]=mapped_column(Integer,default=0)

def reserve(provider:str, cents:int)->None:
    if cents<=0: raise ValueError("Invalid reservation")
    ceiling=int(os.getenv("META_APP_BUDGET_CENTS","500") if provider=="meta" else os.getenv("OTHER_APP_BUDGET_CENTS","100"))
    if ceiling<0: raise ValueError("Invalid budget")
    with SessionLocal.begin() as db:
        # Create the sentinel row if absent. Conflict-safe across concurrent workers.
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sq_insert
        stmt=(pg_insert if db.bind.dialect.name=="postgresql" else sq_insert)(ApiBudget).values(provider=provider,reserved_cents=0).on_conflict_do_nothing(index_elements=["provider"])
        db.execute(stmt)
        result=db.execute(update(ApiBudget).where(ApiBudget.provider==provider,ApiBudget.reserved_cents+cents<=ceiling).values(reserved_cents=ApiBudget.reserved_cents+cents))
        if result.rowcount!=1: raise ValueError("App inference budget reached; no external call made")

def budget_status(provider:str)->dict:
    ceiling=int(os.getenv("META_APP_BUDGET_CENTS","500") if provider=="meta" else os.getenv("OTHER_APP_BUDGET_CENTS","100"))
    with SessionLocal() as db:
        used=db.scalar(select(ApiBudget.reserved_cents).where(ApiBudget.provider==provider)) or 0
    return {"provider":provider,"reserved_usd":round(used/100,2),"cap_usd":round(ceiling/100,2),"remaining_usd":round(max(0,ceiling-used)/100,2),"note":"Conservative app reservations; not provider billing or account-wide hard cap."}
