import io
import json
import wave

from app.meta_client import MetaClient, MetaError
from app.workspace_store import SessionLocal, WorkflowRun


def sample_wav(seconds=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(24000)
        clip.writeframes(b"\x00\x00" * (24000 * seconds))
    return output.getvalue()


def post_voice(client, workspace_id, audio=None, consent="true"):
    return client.post("/api/v1/prompts/transcribe", data={
        "workspace_id": workspace_id, "consent": consent,
    }, files={"file": ("prompt.wav", audio if audio is not None else sample_wav(), "audio/wav")})


def configure_live(monkeypatch):
    monkeypatch.setenv("INFERENCE_PROVIDER", "meta")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE", "true")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL", "true")
    monkeypatch.setenv("SENTINELX_MODE", "live")
    monkeypatch.setenv("MODEL_API_KEY", "test-only-key")


def test_prompt_dictation_requires_consent_and_valid_audio(authenticated_client, monkeypatch):
    client = authenticated_client
    workspace = client.post("/api/v1/workspaces", json={"name": "Prompt voice"}).json()["id"]
    configure_live(monkeypatch)
    assert post_voice(client, workspace, consent="false").status_code == 422
    assert post_voice(client, workspace, audio=b"not-wav").status_code == 422


def test_prompt_dictation_requires_live_meta_without_sample_fallback(authenticated_client, monkeypatch):
    client = authenticated_client
    workspace = client.post("/api/v1/workspaces", json={"name": "Voice gates"}).json()["id"]
    monkeypatch.setenv("INFERENCE_PROVIDER", "demo")
    monkeypatch.setenv("ALLOW_PAID_INFERENCE", "false")
    monkeypatch.setenv("ENABLE_LIVE_MULTIMODAL", "false")
    assert post_voice(client, workspace).status_code == 503


def test_prompt_dictation_uses_owned_budgeted_meta_and_does_not_persist_audio_or_transcript(
    authenticated_client, monkeypatch
):
    client = authenticated_client
    workspace = client.post("/api/v1/workspaces", json={"name": "Voice prompt"}).json()["id"]
    configure_live(monkeypatch)
    calls = []

    def transcribe(self, payload, mime):
        calls.append((payload, mime, self.owner_id, self.workspace_id, self.run_id))
        return {"provenance": "live_meta", "model": "muse-voice-transcribe-1.0",
                "data": {"transcript": "Find better qualified local inquiries."}}

    monkeypatch.setattr(MetaClient, "transcribe", transcribe)
    response = post_voice(client, workspace)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["provenance"] == "live_meta"
    assert data["transcript"] == "Find better qualified local inquiries."
    assert len(calls) == 1 and calls[0][1] == "audio/wav" and calls[0][3] == workspace
    assert calls[0][0] == sample_wav()
    with SessionLocal() as db:
        run = db.get(WorkflowRun, calls[0][4])
        saved = json.loads(run.result_json)
        assert run.status == "inferred"
        assert "transcript" not in saved and "audio" not in saved


def test_prompt_dictation_rejects_another_workspaces_id(authenticated_client, monkeypatch):
    configure_live(monkeypatch)
    response = post_voice(authenticated_client, "not-owned-workspace")
    assert response.status_code == 404


def test_failed_prompt_transcription_returns_no_sample_and_records_failure(authenticated_client, monkeypatch):
    client = authenticated_client
    workspace = client.post("/api/v1/workspaces", json={"name": "Failed voice"}).json()["id"]
    configure_live(monkeypatch)
    calls = []

    def fail(self, payload, mime):
        calls.append(True)
        raise MetaError("Meta transcription failed; no automatic retry. Usage may have been consumed.")

    monkeypatch.setattr(MetaClient, "transcribe", fail)
    response = post_voice(client, workspace)
    assert response.status_code == 502 and "transcript" not in response.json()
    assert len(calls) == 1
    with SessionLocal() as db:
        row = db.query(WorkflowRun).filter(WorkflowRun.workspace_id == workspace).one()
        assert row.status == "failed"
        assert "transcript" not in json.loads(row.result_json)
