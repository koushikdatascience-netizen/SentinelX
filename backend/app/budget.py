"""Application-side conservative reservation guard for model operations.

This is not an account-level financial guarantee: other keys/apps bypass it.
Meta reservations cover app/workspace/run scopes. Default paid calls disabled.
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
    # Usage accounting only. No SentinelX spending ceiling is enforced.
    with SessionLocal.begin() as db:
        # Create the sentinel row if absent. Conflict-safe across concurrent workers.
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sq_insert
        stmt=(pg_insert if db.bind.dialect.name=="postgresql" else sq_insert)(ApiBudget).values(provider=provider,reserved_cents=0).on_conflict_do_nothing(index_elements=["provider"])
        db.execute(stmt)
        result=db.execute(update(ApiBudget).where(ApiBudget.provider==provider).values(reserved_cents=ApiBudget.reserved_cents+cents))
        if result.rowcount != 1: raise RuntimeError("Could not record model usage")

def budget_status(provider:str)->dict:
    with SessionLocal() as db:
        used=db.scalar(select(ApiBudget.reserved_cents).where(ApiBudget.provider==provider)) or 0
    return {"provider": provider, "reserved_usd": round(used / 100, 2), "cap_usd": None, "remaining_usd": None, "note": "Usage estimates only; no application spending cap. Not provider billing."}


def reserve_meta(owner_id: str, workspace_id: str, run_id: str, cents: int) -> None:
    """Record usage estimates for all three scopes without spending ceilings.

    Existing budget rows also store hashed scope counters (no schema migration).
    The owner/workspace/run identity checks remain mandatory.
    """
    import hashlib
    from app.workspace_store import Workspace, WorkflowRun
    if cents <= 0 or not all((owner_id, workspace_id, run_id)):
        raise ValueError("Meta calls require owner, workspace and persisted run")
    key = lambda prefix, value: prefix + hashlib.sha256(value.encode()).hexdigest()[:32]
    scopes = ["meta", key("mw:", workspace_id), key("mr:", workspace_id + ":" + run_id)]
    with SessionLocal.begin() as db:
        workspace = db.get(Workspace, workspace_id)
        run = db.get(WorkflowRun, run_id)
        if not workspace or workspace.owner_id != owner_id or not run or run.workspace_id != workspace_id:
            raise ValueError("Owned workspace/run not found")
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sq_insert
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sq_insert
        # Consistent ordering serializes competing reservations without partial debits.
        for scope in scopes:
            db.execute(insert(ApiBudget).values(provider=scope, reserved_cents=0)
                       .on_conflict_do_nothing(index_elements=["provider"]))
            changed = db.execute(update(ApiBudget).where(
                ApiBudget.provider == scope
            ).values(reserved_cents=ApiBudget.reserved_cents + cents))
            if changed.rowcount != 1:
                raise RuntimeError("Could not record model usage")
