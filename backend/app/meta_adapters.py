"""Explicit provider boundaries. No false claims of visual/audio inference."""
import os
from fastapi import HTTPException
from pydantic import BaseModel

class CapabilityStatus(BaseModel):
    capability:str
    mode:str
    note:str

def capabilities():
    active=os.getenv("INFERENCE_PROVIDER","demo")=="meta" and os.getenv("ALLOW_PAID_INFERENCE")=="true" and os.getenv("ENABLE_LIVE_MULTIMODAL")=="true" and bool(os.getenv("MODEL_API_KEY"))
    return [
        CapabilityStatus(capability="reasoning",mode="configured_not_tested" if active else "mock",note="MetaClient Chat Completions contract documented; live-account output unverified"),
        CapabilityStatus(capability="image",mode="configured_not_tested" if active else "sample",note="MetaClient single-image contract documented; live-account output unverified"),
        CapabilityStatus(capability="voice",mode="not_implemented",note="Muse Voice transcription adapter pending account access and verified API schema"),
        CapabilityStatus(capability="segmentation",mode="not_implemented",note="SAM 3.1 adapter pending account access and verified API schema"),
    ]
