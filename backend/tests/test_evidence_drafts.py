import json
from uuid import uuid4
from unittest.mock import Mock

import pytest

from app import evidence_drafts
from app.providers import ProviderConfig


EXCERPT = "We make custom wooden furniture and offer consultations for residential projects."


@pytest.fixture
def setup_draft(authenticated_client, monkeypatch):
    client = authenticated_client
    wid = client.post("/api/v1/workspaces", json={"name": "Draft workshop"}).json()["id"]
    monkeypatch.setenv("ENABLE_EVIDENCE_INFERENCE", "true")
    monkeypatch.setenv("EVIDENCE_WORKSPACE_MAX_REQUESTS", "1")
    monkeypatch.setattr(evidence_drafts, "configured_provider", lambda: ProviderConfig(
        "meta", "https://api.meta.ai/v1", "muse-spark-1.3", "test-only"))
    analysis = {
        "recommendations": [{"action": "Clarify the consultation request step",
                             "reason": "The supplied excerpt mentions consultations.",
                             "source_id": "E1", "quote": "offer consultations", "priority": "high"}],
        "assumptions": ["Consultation availability is not independently verified."],
        "artifact": {"title": "Homepage copy draft", "body": "Custom wooden furniture for your home. [Add verified contact details]."},
    }
    provider = Mock(return_value={"status": "completed", "text": json.dumps(analysis),
                                 "usage": {"prompt_tokens": 100, "completion_tokens": 200},
                                 "finish_reason": "stop"})
    monkeypatch.setattr(evidence_drafts, "infer", provider)
    body = {"website": "https://example.org", "goal": "Improve qualified furniture inquiries",
            "page_title": "Workshop", "page_excerpt": EXCERPT, "request_id": str(uuid4())}
    return client, wid, body, provider, analysis


def test_draft_persisted_exported_and_reused_without_second_call(setup_draft):
    client, wid, body, provider, _ = setup_draft
    path = f"/api/v1/workspaces/{wid}/evidence-draft"
    assert client.get(path + "/status").json()["remaining"] == 1
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "inferred"
    assert run["result"]["evidence"][0]["source_type"] == "user_supplied_unverified"
    assert run["result"]["external_actions_performed"] == 0
    assert run["result"]["artifact_status"] == "draft_requires_review"
    replay = client.post(path, json=body)
    assert replay.status_code == 200
    assert replay.json()["id"] == run["id"]
    provider.assert_called_once()
    status = client.get(path + "/status").json()
    assert status["remaining"] == 0 and status["enabled"] is False
    assert EXCERPT in provider.call_args.args[0]
    report = client.get(f"/api/v1/workspaces/{wid}/runs/{run['id']}/report")
    assert report.status_code == 200
    assert "Homepage copy draft" in report.text
    assert "muse-spark-1.3" in report.text
    assert "no independent fact verification" in report.text
    assert client.post(path, json={**body, "goal": "A changed business objective"}).status_code == 409
    assert client.post(path, json={**body, "request_id": str(uuid4())}).status_code == 429
    provider.assert_called_once()


@pytest.mark.parametrize("failure", ["bad_json", "bad_quote", "bad_source", "extra_fields", "timeout"])
def test_failed_generation_persisted_without_retry_or_raw_response(setup_draft, failure):
    client, wid, body, provider, analysis = setup_draft
    if failure == "timeout":
        provider.side_effect = RuntimeError("private-provider-response-do-not-store")
    else:
        if failure == "bad_quote": analysis["recommendations"][0]["quote"] = "Made up source quotation"
        if failure == "bad_source": analysis["recommendations"][0]["source_id"] = "E2"
        if failure == "extra_fields": analysis["executed"] = True
        provider.return_value["text"] = "private-provider-response-do-not-store" if failure == "bad_json" else json.dumps(analysis)
    path = f"/api/v1/workspaces/{wid}/evidence-draft"
    response = client.post(path, json=body)
    assert response.status_code == 502, response.text
    assert client.post(path, json=body).status_code == 409
    provider.assert_called_once()
    run = client.get(f"/api/v1/workspaces/{wid}/runs").json()[0]
    assert run["status"] == "failed"
    saved = client.get(f"/api/v1/workspaces/{wid}/runs/{run['id']}").json()
    assert "private-provider-response-do-not-store" not in json.dumps(saved)
    assert "analysis" not in saved["result"]


def test_disabled_and_zero_quota_do_not_call_provider(setup_draft, monkeypatch):
    client, wid, body, provider, _ = setup_draft
    path = f"/api/v1/workspaces/{wid}/evidence-draft"
    monkeypatch.setenv("ENABLE_EVIDENCE_INFERENCE", "false")
    assert client.post(path, json=body).status_code == 403
    monkeypatch.setenv("ENABLE_EVIDENCE_INFERENCE", "true")
    monkeypatch.setenv("EVIDENCE_WORKSPACE_MAX_REQUESTS", "0")
    assert client.post(path, json=body).status_code == 422
    provider.assert_not_called()


def test_foreign_owner_cannot_generate_or_read_draft(setup_draft):
    client, wid, body, provider, _ = setup_draft
    run = client.post(f"/api/v1/workspaces/{wid}/evidence-draft", json=body).json()
    credentials = {"email": f"other-{uuid4()}@example.org", "password": "StrongPassword123"}
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    token = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.post(f"/api/v1/workspaces/{wid}/evidence-draft", json=body).status_code == 404
    assert client.get(f"/api/v1/workspaces/{wid}/runs/{run['id']}").status_code == 404
    assert client.get(f"/api/v1/workspaces/{wid}/runs/{run['id']}/report").status_code == 404
    assert client.get(f"/api/v1/workspaces/{wid}/evidence-draft/status").status_code == 404
    provider.assert_called_once()


def test_duplicate_while_pending_does_not_call_provider_again(setup_draft):
    client, wid, body, provider, _ = setup_draft
    path = f"/api/v1/workspaces/{wid}/evidence-draft"
    result = provider.return_value

    def in_flight(prompt, **scope):
        assert client.post(path, json=body).status_code == 409
        return result

    provider.side_effect = in_flight
    assert client.post(path, json=body).status_code == 201
    provider.assert_called_once()


def test_concurrent_requests_share_one_workspace_attempt(setup_draft):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    client, wid, body, provider, _ = setup_draft
    start = Barrier(2)

    def attempt(_):
        start.wait(timeout=5)
        return client.post(f"/api/v1/workspaces/{wid}/evidence-draft", json={
            **body, "request_id": str(uuid4())}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(attempt, range(2)))
    assert sorted(statuses) == [201, 429]
    provider.assert_called_once()


def test_campaign_requires_complete_pack_and_exports(setup_draft):
    client, wid, body, provider, analysis = setup_draft
    body["deliverable"] = "campaign"
    analysis["campaign"] = {"audience":"Local furniture makers", "angle":"Clear quotation requests",
        "captions":["Prepare a drawing for review.","Discuss a custom furniture project.","Request a workshop consultation."],
        "call_to_action":"[Add verified contact]", "experiment":"Count qualified enquiries for seven days."}
    provider.return_value["text"] = json.dumps(analysis)
    response = client.post(f"/api/v1/workspaces/{wid}/evidence-draft",json=body)
    assert response.status_code == 201, response.text
    report = client.get(f"/api/v1/workspaces/{wid}/runs/{response.json()['id']}/report")
    assert "Caption 3: Request a workshop consultation." in report.text
    assert "campaign" in provider.call_args.args[0]


def test_campaign_rejects_missing_pack_and_long_caption():
    from app.evidence_drafts import validate_analysis
    data={"recommendations":[{"action":"Review consultation messaging", "reason":"The source mentions consultations.",
        "source_id":"E1","quote":"offer consultations","priority":"high"}],"assumptions":[],
        "artifact":{"title":"Campaign draft","body":"Draft copy requiring owner verification."}}
    with pytest.raises(ValueError,match="missing"):
        validate_analysis(json.dumps(data),EXCERPT,"campaign")
    data["campaign"]={"audience":"Local furniture makers","angle":"Clarify enquiries","captions":["x"*351,"second","third"],
        "call_to_action":"Ask the owner", "experiment":"Count enquiries for seven days."}
    with pytest.raises(ValueError,match="caption"):
        validate_analysis(json.dumps(data),EXCERPT,"campaign")
