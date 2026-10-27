"""Local/CI test server only. Never included in the backend Docker image.

Only the evidence-draft provider boundary is stubbed; auth, DB, validation,
quotas, reviews, reporting and frontend requests use the actual application.
"""
import json
import os

os.environ["ENABLE_EVIDENCE_INFERENCE"] = "true"
os.environ["EVIDENCE_WORKSPACE_MAX_REQUESTS"] = "1"

from app.main import app
from app import evidence_drafts
from app.providers import ProviderConfig


def offline_infer(prompt):
    evidence = json.JSONDecoder().raw_decode(prompt.split("JSON:\n", 1)[1])[0]["E1"]["excerpt"]
    return {"status": "completed", "finish_reason": "stop", "usage": None,
            "text": json.dumps({
                "recommendations": [{"action": "Review consultation messaging",
                                     "reason": "Offline test fixture interpretation only.",
                                     "source_id": "E1", "quote": evidence[:30], "priority": "high"}],
                "assumptions": ["This is an offline browser test fixture, not real AI inference."],
                "campaign": {"audience":"Local furniture makers","angle":"Clarify quotation intake","captions":["Prepare your drawing for review.","Discuss your custom project.","Ask about workshop services."],"call_to_action":"[Add verified contact]","experiment":"Count qualified enquiries for seven days."},
                "artifact": {"title": "Offline fixture draft", "body": "Test-only draft. [Owner to supply verified contact information]."}})}


evidence_drafts.configured_provider = lambda: ProviderConfig(
    "mock_test_provider", "http://127.0.0.1", "offline-fixture", "not-a-key")
evidence_drafts.infer = offline_infer
