"""Explicit, owner-scoped voice dictation for AI prompt fields."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import current_user
from app.campaign_routes import generation_is_live
from app.engine_inputs import wav_duration
from app.meta_client import MetaClient, MetaError
from app.workspace_routes import create_model_run, finish_model_run, owned
from app.workspace_store import User, session

router = APIRouter(prefix="/api/v1/prompts", tags=["Prompt dictation"])


@router.post("/transcribe")
async def transcribe_prompt(
    workspace_id: str = Form(...),
    consent: bool = Form(False),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(session),
):
    owned(db, user, workspace_id)
    if not consent:
        raise HTTPException(422, "Consent to send this recording to Meta for transcription is required")
    if not generation_is_live(user, "live"):
        raise HTTPException(503, "Live Meta transcription is unavailable; no audio was sent")

    payload = await file.read(3_000_001)
    try:
        duration_ms = wav_duration(payload, file.content_type or "")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    run = create_model_run(db, workspace_id, "prompt-dictation", "Voice prompt transcription")
    try:
        result = MetaClient(owner_id=user.id, workspace_id=workspace_id, run_id=run.id).transcribe(
            payload, file.content_type or ""
        )
        transcript = result.get("data", {}).get("transcript")
        if result.get("provenance") != "live_meta" or not isinstance(transcript, str) or not transcript.strip():
            raise MetaError("No live transcript was returned; no sample was substituted")
        if len(transcript) > 8000:
            raise MetaError("Transcript exceeded the supported length")
        finish_model_run(db, run, "inferred", "live_meta")
        # Audio and transcript are deliberately not persisted in the workspace.
        return {"provenance": "live_meta", "model": result["model"],
                "transcript": transcript.strip(), "audio_duration_ms": duration_ms}
    except MetaError as exc:
        finish_model_run(db, run, "failed", "live_meta", "prompt_transcription_failed")
        raise HTTPException(502, str(exc)) from None
    except Exception:
        finish_model_run(db, run, "failed", "live_meta", "prompt_transcription_failed")
        raise HTTPException(502, "Meta transcription failed; no automatic retry") from None
