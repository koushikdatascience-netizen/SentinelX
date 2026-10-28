"""Local/CI test server only. Never included in the backend Docker image.

Only the evidence-draft provider boundary is stubbed; auth, DB, validation,
quotas, reviews, reporting and frontend requests use the actual application.
"""
import json
import os

os.environ["ENABLE_EVIDENCE_INFERENCE"] = "true"
os.environ["EVIDENCE_WORKSPACE_MAX_REQUESTS"] = "1"
os.environ["ENABLE_RESEARCH_WORKER"] = "true"

from app.main import app
from app import evidence_drafts
from app.providers import ProviderConfig


def offline_infer(prompt, **scope):
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

# Offline browser evidence: exercise the real durable crawler, parser, storage,
# review and report routes with only the public HTTP transport replaced.
from app import site_research
from tests.test_site_research import response,HOME
from urllib.parse import urlsplit

def research_fixture(url,**kwargs):
    if urlsplit(url).hostname!="fixture.example":raise ValueError("Offline browser test allows fixture.example only")
    if url.endswith("robots.txt"):return response(url,"User-agent: *\nDisallow: /private")
    if url.endswith("sitemap.xml"):return response(url,'<urlset><url><loc>https://fixture.example/contact</loc></url></urlset>')
    return response(url,HOME if url.endswith("/") else '<title>Workshop contact</title><h1>Contact the workshop</h1><p>Send your quantity, drawings and required date to request a quote.</p>')

site_research.request_public=research_fixture
