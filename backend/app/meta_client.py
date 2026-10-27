"""Single Meta Model API access boundary. Officially documented shapes; no implicit spending.

Docs: https://dev.meta.ai/docs/protocols/chat-completions
      https://dev.meta.ai/docs/structured-output
      https://dev.meta.ai/docs/image-generation
      https://dev.meta.ai/docs/api-reference/chat-completions/schemas
"""
import base64
import json
import os
from typing import Any

from openai import OpenAI
from app.budget import reserve


class NotSupported(RuntimeError):
    """Model API operation lacks a verified adapter."""


class MetaResponseError(RuntimeError):
    """A response was empty, incomplete, or unsuitable for use."""


class MetaClient:
    def __init__(self, sdk_factory=OpenAI):
        self.sdk_factory = sdk_factory
        self._actual_transport = sdk_factory is OpenAI

    def _record_success(self, capability: str, model: str) -> None:
        # Never treat mocked tests or a merely configured key as verified live access.
        if not self._actual_transport:return
        try:
            from app.workspace_store import MetaCapabilityCheck, SessionLocal, utcnow
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            with SessionLocal.begin() as db:
                ins=pg_insert if db.bind.dialect.name=="postgresql" else sqlite_insert
                stmt=ins(MetaCapabilityCheck).values(
                    capability=capability,model=model,succeeded_at=utcnow())
                db.execute(stmt.on_conflict_do_update(index_elements=["capability"],
                    set_={"model":model,"succeeded_at":utcnow()}))
        except Exception:
            # Response remains usable even if status persistence is temporarily down.
            pass

    @staticmethod
    def _enabled(multimodal: bool) -> bool:
        return (
            os.getenv("ALLOW_PAID_INFERENCE", "false").lower() == "true"
            and os.getenv("ENABLE_LIVE_MULTIMODAL", "false").lower() == "true"
            and os.getenv("INFERENCE_PROVIDER", "demo").lower() == "meta"
            and os.getenv("SENTINELX_MODE", "demo").lower() == "live"
        )

    def _sdk(self):
        key = os.getenv("MODEL_API_KEY")
        if not key:
            raise ValueError("MODEL_API_KEY is not configured")
        return self.sdk_factory(api_key=key, base_url="https://api.meta.ai/v1", timeout=45, max_retries=0)

    @staticmethod
    def _format(schema: dict | None):
        if schema is None:
            return None
        if schema.get("type") != "object":
            raise ValueError("Structured output root schema must be an object")
        return {"type": "json_schema", "json_schema": {"name": "SentinelXResult", "schema": schema}}

    def _completion(self, messages: list[dict], schema: dict | None, multimodal: bool) -> dict:
        model = os.getenv("META_MODEL", "muse-spark-1.3")
        if not self._enabled(multimodal):
            return {"provenance": "sample", "model": model, "data": {"note": "No Meta request made; deterministic sample response."}}
        # Reserve BEFORE any external request; conservatively retained on errors.
        reserve("meta", 5 if not multimodal else 10)
        kw: dict[str, Any] = {"model": model, "messages": messages,
                               "max_completion_tokens": 1200,
                               "extra_body": {"reasoning_effort": "minimal"}}
        fmt = self._format(schema)
        if fmt: kw["response_format"] = fmt
        result = self._sdk().chat.completions.create(**kw)
        if not result.choices or result.choices[0].finish_reason != "stop":
            raise MetaResponseError("Meta response incomplete or truncated")
        content = result.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise MetaResponseError("Meta returned no visible content")
        try:
            data = json.loads(content) if schema else {"text": content}
        except json.JSONDecodeError as exc:
            raise MetaResponseError("Meta returned malformed structured JSON") from exc
        if schema and not isinstance(data, dict):
            raise MetaResponseError("Expected structured JSON object")
        usage=getattr(result,"usage",None)
        detail=getattr(usage,"completion_tokens_details",None)
        self._record_success("vision" if multimodal else "text", model)
        return {"provenance":"live_meta","model":model,"data":data,"finish_reason":"stop",
                "usage":{"prompt_tokens":getattr(usage,"prompt_tokens",None),
                         "completion_tokens":getattr(usage,"completion_tokens",None),
                         "reasoning_tokens":getattr(detail,"reasoning_tokens",None)}}

    def text(self, system: str, user: str, json_schema: dict | None = None) -> dict:
        return self._completion([{"role": "system", "content": system[:4000]},
                                 {"role": "user", "content": user[:10000]}], json_schema, False)

    def vision(self, image_bytes: bytes, mime: str, prompt: str, json_schema: dict | None = None) -> dict:
        if mime not in ("image/png", "image/jpeg", "image/webp") or not image_bytes or len(image_bytes) > 5_000_000:
            raise ValueError("Only PNG/JPEG/WebP images up to 5MB are accepted")
        if not self._enabled(True):
            return {"provenance": "sample", "model": os.getenv("META_MODEL", "muse-spark-1.3"),
                    "data": {"note": "Image was not analyzed by Meta."}}
        image_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        return self._completion([{"role": "user", "content": [
            {"type": "text", "text": prompt[:4000]},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]}], json_schema, True)

    def image(self, prompt: str, size: str = "1024x1024") -> dict:
        if not 15 <= len(prompt) <= 1500 or size not in ("1024x1024", "1024x1536", "1536x1024"):
            raise ValueError("Invalid prompt or image size")
        if not self._enabled(True):
            return {"provenance": "sample", "model": "muse-image-1.0",
                    "data": {"note": "No image generated.", "image_b64": None}}
        reserve("meta", 2)  # 1 cent image + conservative additional reservation
        result = self._sdk().images.generate(model="muse-image-1.0", prompt=prompt, size=size, n=1)
        if not result.data or not getattr(result.data[0], "b64_json", None):
            raise MetaResponseError("Meta did not return embedded image bytes")
        self._record_success("image", "muse-image-1.0")
        return {"provenance": "live_meta", "model": "muse-image-1.0",
                "data": {"image_b64": result.data[0].b64_json}}

    def segment(self, image_bytes: bytes, mime: str) -> dict:
        if not self._enabled(True):
            return {"provenance": "sample", "model": "sam-3.1",
                    "data": {"note": "Segmentation not run."}}
        raise NotSupported("SAM 3.1 uses the Responses/Files APIs; exact request and mask extraction need separate validated implementation. No charge made.")
