"""Explicit, owner-scoped voice dictation for AI prompt fields."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from uuid import UUID
import hashlib
import json
from sqlalchemy.orm import Session

from app.auth import current_user
from app.campaign_routes import generation_is_live
from app.engine_inputs import wav_duration
from app.meta_client import MetaClient, MetaError
from app.workspace_routes import create_model_run, finish_model_run, owned
from app.workspace_store import User,WorkflowRun,session
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/v1/prompts", tags=["Prompt dictation"])


@router.post("/transcribe")
async def transcribe_prompt(
    workspace_id: str = Form(...),
    consent: bool = Form(False),
    file: UploadFile = File(...),
    request_id:UUID|None=Form(None),
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

    if request_id:
        previous=db.get(WorkflowRun,str(request_id))
        if previous:
            if previous.workspace_id!=workspace_id:raise HTTPException(404,"Recording request not found")
            raise HTTPException(409,"This recording already had a transcription request. No duplicate paid call was made; record a new prompt if needed.")
        run=WorkflowRun(id=str(request_id),workspace_id=workspace_id,website="prompt-dictation",objective="Voice prompt transcription",status="pending",result_json=json.dumps({"operation":"prompt_transcription","audio_sha256":hashlib.sha256(payload).hexdigest()}))
        db.add(run)
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,"This recording request already exists; no duplicate paid call was made") from None
    else:run = create_model_run(db, workspace_id, "prompt-dictation", "Voice prompt transcription")
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
    except ValueError as exc:
        finish_model_run(db, run, "failed", "live_meta", "prompt_transcription_failed")
        if str(exc).startswith("Meta budget reached"):
            raise HTTPException(429,"Voice transcription reached the configured AI spending cap. No audio was sent to Meta; this is not a microphone-permission error.") from None
        raise HTTPException(502,"Voice transcription failed validation; no automatic retry") from None
    except Exception:
        finish_model_run(db, run, "failed", "live_meta", "prompt_transcription_failed")
        raise HTTPException(502, "Meta transcription failed; no automatic retry") from None
