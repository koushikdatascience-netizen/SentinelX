"""Capabilities and honest access status; registry membership is not API access."""
from enum import Enum
from pydantic import BaseModel

class Availability(str, Enum):
    mock = "mock_only"
    configured = "configured_not_verified"

class ModelCapability(BaseModel):
    model: str
    purpose: str
    provider: str = "Meta"
    access: Availability = Availability.mock

CAPABILITIES = (
    ("muse-spark-1.3", "reasoning_and_research"),
    ("muse-wonder", "complex_planning"),
    ("sam-3.1", "visual_segmentation"),
    ("muse-image-1.0", "creative_generation"),
    ("muse-voice-transcribe-1.0", "speech_transcription"),
    ("muse-spark-open", "open_weight_reasoning"),
    ("muse-glimmer", "edge_inference"),
)

def catalog(configured_model: str | None = None) -> list[ModelCapability]:
    return [
        ModelCapability(
            model=model,
            purpose=purpose,
            access=Availability.configured if model == configured_model else Availability.mock,
        ) for model,purpose in CAPABILITIES
    ]
