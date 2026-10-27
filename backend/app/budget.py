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


def reserve_meta(owner_id: str, workspace_id: str, run_id: str, cents: int) -> None:
    """Atomically reserve all three scopes; never refund uncertain provider failures.

    Existing budget rows also store hashed scope counters (no schema migration).
    Scope ceilings default to zero until explicitly configured by an operator.
    """
    import hashlib
    from app.workspace_store import Workspace, WorkflowRun
    if cents <= 0 or not all((owner_id, workspace_id, run_id)):
        raise ValueError("Meta calls require owner, workspace and persisted run")
    key = lambda prefix, value: prefix + hashlib.sha256(value.encode()).hexdigest()[:32]
    limits = [("meta", int(os.getenv("META_APP_BUDGET_CENTS", "500"))),
              (key("mw:", workspace_id), int(os.getenv("META_WORKSPACE_BUDGET_CENTS", "0"))),
              (key("mr:", workspace_id + ":" + run_id), int(os.getenv("META_RUN_BUDGET_CENTS", "0")))]
    with SessionLocal.begin() as db:
        workspace = db.get(Workspace, workspace_id)
        run = db.get(WorkflowRun, run_id)
        if not workspace or workspace.owner_id != owner_id or not run or run.workspace_id != workspace_id:
            raise ValueError("Owned workspace/run not found")
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sq_insert
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sq_insert
        # Consistent ordering serializes competing reservations without partial debits.
        for scope, ceiling in limits:
            if ceiling < cents:
                raise ValueError("Meta budget reached; no external call made")
            db.execute(insert(ApiBudget).values(provider=scope, reserved_cents=0)
                       .on_conflict_do_nothing(index_elements=["provider"]))
            changed = db.execute(update(ApiBudget).where(
                ApiBudget.provider == scope, ApiBudget.reserved_cents + cents <= ceiling
            ).values(reserved_cents=ApiBudget.reserved_cents + cents))
            if changed.rowcount != 1:
                raise ValueError("Meta budget reached; no external call made")
