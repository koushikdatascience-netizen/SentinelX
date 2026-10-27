"""Only hosted Meta transport. Documentation-verified, not live-account certified."""
import base64
import io
import json
import os
from PIL import Image
from jsonschema import Draft202012Validator
from openai import OpenAI
from app.budget import reserve_meta


class NotSupported(ValueError):
    pass


class MetaError(ValueError):
    """Safe error: never embeds provider responses, prompts or credentials."""


# Authored fixture, not a model-generated image (1x1 PNG).
SAMPLE_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC"


class MetaClient:
    def __init__(self, *, owner_id=None, workspace_id=None, run_id=None, max_tokens=500):
        if not isinstance(max_tokens, int) or not 1 <= max_tokens <= 1200:
            raise ValueError("Output token limit must be 1..1200")
        self.owner_id, self.workspace_id, self.run_id = owner_id, workspace_id, run_id
        self.max_tokens = max_tokens

    def _live(self):
        # Both flags gate every capability, including text, per operator policy.
        return (os.getenv("INFERENCE_PROVIDER", "demo") == "meta"
                and os.getenv("ALLOW_PAID_INFERENCE", "false") == "true"
                and os.getenv("ENABLE_LIVE_MULTIMODAL", "false") == "true")

    def _client(self, cents):
        key = os.getenv("MODEL_API_KEY", "")
        if not key:
            raise MetaError("MODEL_API_KEY is required for live Meta calls")
        reserve_meta(self.owner_id, self.workspace_id, self.run_id, cents)
        return OpenAI(api_key=key, base_url="https://api.meta.ai/v1", timeout=30, max_retries=0)

    @staticmethod
    def _prompt(value, maximum):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError("Invalid or oversized prompt")

    @staticmethod
    def _schema(schema):
        if schema is None:
            return None
        if not isinstance(schema, dict) or len(json.dumps(schema)) > 16000:
            raise ValueError("Invalid or oversized JSON schema")
        # Never resolve remote refs (SSRF) or recursive refs in local validation.
        def check(node):
            if isinstance(node, dict):
                if any(key in node for key in ("$ref", "$dynamicRef", "$recursiveRef")):
                    raise NotSupported("Schema references are not supported by this bounded client; inline the schema")
                for value in node.values(): check(value)
            elif isinstance(node, list):
                for value in node: check(value)
        check(schema)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception:
            raise MetaError("Invalid JSON schema") from None
        return Draft202012Validator(schema)

    @staticmethod
    def _fixture(schema):
        # Small deterministic fixture generator, explicitly not model output.
        if "const" in schema: return schema["const"]
        if "enum" in schema: return schema["enum"][0]
        if "anyOf" in schema: return MetaClient._fixture(schema["anyOf"][0])
        kind = schema.get("type", "object")
        if isinstance(kind, list): kind = kind[0]
        if kind == "object":
            return {k: MetaClient._fixture(v) for k,v in schema.get("properties", {}).items()}
        if kind == "array":
            count = schema.get("minItems", 0)
            if count > 10: raise NotSupported("Sample array fixture limit exceeded")
            return [MetaClient._fixture(schema.get("items", {})) for _ in range(count)]
        if kind == "string": return "Sample fixture".ljust(min(schema.get("minLength", 0), 1000), "x")[:schema.get("maxLength", 1000)]
        if kind in ("integer", "number"): return schema.get("minimum", 0)
        if kind == "boolean": return False
        if kind == "null": return None
        raise NotSupported("No sample fixture for this schema")

    @staticmethod
    def _image_input(image_bytes, mime):
        formats = {"image/png":"PNG", "image/jpeg":"JPEG", "image/webp":"WEBP"}
        if mime not in formats or not isinstance(image_bytes, bytes) or not 0 < len(image_bytes) <= 5_000_000:
            raise ValueError("Image must be PNG/JPEG/WebP and at most 5 MB")
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                if image.format != formats[mime] or image.width*image.height > 20_000_000:
                    raise ValueError()
                image.verify()
        except Exception:
            raise ValueError("Invalid image or excessive pixel count") from None
        return "data:" + mime + ";base64," + base64.b64encode(image_bytes).decode()

    def _chat(self, messages, schema):
        validator = self._schema(schema)
        model = "muse-spark-1.3"
        if not self._live():
            data = self._fixture(schema) if schema is not None else "Sample fixture: no Meta inference performed."
            if validator and not validator.is_valid(data):
                raise NotSupported("No valid deterministic fixture for this schema")
            return {"provenance":"sample", "model":model, "data":data, "usage":None, "finish_reason":None}
        options = {}
        if schema is not None:
            options["response_format"] = {"type":"json_schema", "json_schema":{
                "name":"sentinelx_output", "schema":schema, "strict":False}}
        if os.getenv("META_MODEL", model) != model:
            raise NotSupported("UNVERIFIED text model; only muse-spark-1.3 is supported")
        try:
            with self._client(5) as client:
                response = client.chat.completions.create(model=model, messages=messages,
                    reasoning_effort="minimal", max_completion_tokens=self.max_tokens, **options)
                choice = response.choices[0] if response.choices else None
                text = (choice.message.content or "").strip() if choice else ""
                if not text or choice.finish_reason != "stop":
                    raise MetaError("Empty or incomplete Meta output. No retry made; usage may have been consumed.")
                data = json.loads(text) if validator else text
                if validator and not validator.is_valid(data):
                    raise MetaError("Meta output did not match schema. No retry made; usage may have been consumed.")
                usage = response.usage
                details = getattr(usage, "completion_tokens_details", None)
                return {"provenance":"live_meta", "model":model, "data":data, "finish_reason":"stop",
                        "usage":{"prompt_tokens":getattr(usage,"prompt_tokens",None),
                                 "completion_tokens":getattr(usage,"completion_tokens",None),
                                 "reasoning_tokens":getattr(details,"reasoning_tokens",None)}}
        except (MetaError, NotSupported):
            raise
        except ValueError as error:
            # Budget errors are safe, validation/provider errors are not echoed.
            if str(error).startswith(("Meta budget", "Owned workspace", "Meta calls require")): raise
            raise MetaError("Meta validation failed. No retry made; usage may have been consumed.") from None
        except Exception:
            raise MetaError("Meta request failed. No retry made; usage may have been consumed.") from None

    def text(self, system, user, json_schema=None):
        self._prompt(system, 2000)
        self._prompt(user, 6000)
        return self._chat([{"role":"developer", "content":system}, {"role":"user", "content":user}], json_schema)

    def vision(self, image_bytes, mime, prompt, json_schema=None):
        self._prompt(prompt, 2000)
        url = self._image_input(image_bytes, mime)
        return self._chat([{"role":"user", "content":[{"type":"text", "text":prompt},
                           {"type":"image_url", "image_url":{"url":url}}]}], json_schema)

    def image(self, prompt, size):
        self._prompt(prompt, 1500)
        if size not in ("1024x1024", "1024x1536", "1536x1024"):
            raise ValueError("Unsupported image aspect ratio")
        model = "muse-image-1.0"
        if not self._live():
            return {"provenance":"sample", "model":model, "data":{"b64_json":SAMPLE_PNG, "format":"png"}}
        try:
            with self._client(5) as client:
                response = client.images.generate(model=model, prompt=prompt, size=size, n=1, response_format="b64_json")
                if len(response.data or []) != 1 or not response.data[0].b64_json:
                    raise MetaError("Meta returned no image. No retry made; usage may have been consumed.")
                encoded = response.data[0].b64_json
                if len(encoded) > 30_000_000:
                    raise MetaError("Meta image exceeds output size limit")
                decoded=base64.b64decode(encoded, validate=True)
                with Image.open(io.BytesIO(decoded)) as image:
                    if image.format not in ("PNG","JPEG","WEBP") or image.width*image.height > 20_000_000:
                        raise MetaError("Invalid or excessive Meta image output")
                    output_format=image.format.lower()
                    image.verify()
                return {"provenance":"live_meta", "model":model, "data":{"b64_json":encoded, "format":output_format}}
        except MetaError:
            raise
        except Exception:
            raise MetaError("Meta image request failed. No retry made; usage may have been consumed.") from None

    def segment(self, image_bytes, mime):
        self._image_input(image_bytes, mime)
        if not self._live():
            return {"provenance":"sample", "model":"sam-3.1", "data":{"objects":[], "note":"Fixture only; no segmentation performed"}}
        raise NotSupported("UNVERIFIED SAM adapter: object prompt and special-token mask parser are required; no call made")

    def transcribe(self, audio_bytes, mime):
        if not self._live():
            return {"provenance":"sample", "model":"unverified", "data":{"transcript":None}}
        raise NotSupported("UNVERIFIED voice adapter; no call made")
