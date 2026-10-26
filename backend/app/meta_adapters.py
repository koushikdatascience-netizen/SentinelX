"""Explicit provider boundaries. No false claims of visual/audio inference."""
import os
from fastapi import HTTPException
from pydantic import BaseModel

class CapabilityStatus(BaseModel):
    capability:str
    mode:str
    note:str

def capabilities():
    active=os.getenv("SENTINELX_MODE","demo")=="live" and bool(os.getenv("MODEL_API_KEY"))
    return [
        CapabilityStatus(capability="reasoning",mode="configured_not_tested" if active else "mock",note="Meta text responses endpoint; actual authorization not verified"),
        CapabilityStatus(capability="image",mode="not_implemented",note="Muse Image adapter pending account access and verified API schema"),
        CapabilityStatus(capability="voice",mode="not_implemented",note="Muse Voice transcription adapter pending account access and verified API schema"),
        CapabilityStatus(capability="segmentation",mode="not_implemented",note="SAM 3.1 adapter pending account access and verified API schema"),
    ]
