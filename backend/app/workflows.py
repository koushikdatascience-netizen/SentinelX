"""Deterministic approval state machine. Approval does not perform execution."""
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from uuid import uuid4
from pydantic import BaseModel, Field

class State(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"

class ActionRecord(BaseModel):
    id: str
    run_id: str
    kind: str
    description: str
    source_url: str
    state: State = State.proposed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None

class ActionStore:
    def __init__(self):
        self._actions: dict[str, ActionRecord] = {}
        self._lock = RLock()

    def propose(self, run_id: str, kind: str, description: str, source_url: str) -> ActionRecord:
        with self._lock:
            record = ActionRecord(id=str(uuid4()), run_id=run_id, kind=kind, description=description, source_url=source_url)
            self._actions[record.id] = record
            return record.model_copy(deep=True)

    def get(self, action_id: str) -> ActionRecord | None:
        with self._lock:
            rec = self._actions.get(action_id)
            return rec.model_copy(deep=True) if rec else None

    def decide(self, action_id: str, decision: State) -> ActionRecord | None:
        if decision not in (State.approved, State.rejected):
            raise ValueError("Decision must be approved or rejected")
        with self._lock:
            rec = self._actions.get(action_id)
            if rec is None:
                return None
            if rec.state != State.proposed:
                raise ValueError("Action has already been reviewed")
            revised = rec.model_copy(update={"state": decision, "reviewed_at": datetime.now(timezone.utc)})
            self._actions[action_id] = revised
            return revised.model_copy(deep=True)

action_store = ActionStore()
