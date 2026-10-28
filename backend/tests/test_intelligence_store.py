import pytest
from sqlalchemy.exc import IntegrityError
from app.workspace_store import SessionLocal
from app.intelligence_store import BusinessFact
from tests.test_mission_routes import inputs


def test_fact_identity_is_unique_within_workspace_and_independent_across_workspaces(authenticated_client):
    wid=inputs(authenticated_client)["workspace_id"];other=inputs(authenticated_client)["workspace_id"]
    def fact(workspace):return BusinessFact(workspace_id=workspace,fact_key="a"*64,kind="description",value_json='"text"',evidence_json='{}')
    with SessionLocal.begin() as db:db.add(fact(wid));db.add(fact(other))
    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as db:db.add(fact(wid));db.flush()
