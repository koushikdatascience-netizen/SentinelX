# Meta Model API — verified documentation and adapter status (28 Oct 2026)

**Documentation verified, NOT account-specific live tests.** Do not call this module production-verified before gated smoke calls succeed. No paid calls were made while building this module.

| Method | Model / transport | Documentation | Status |
|---|---|---|---|
| `text(system,user,json_schema)` | `muse-spark-1.3`, `POST /v1/chat/completions` using OpenAI client; `response_format.type=json_schema` and `json_schema:{name,schema}` | https://dev.meta.ai/docs/protocols/chat-completions and https://dev.meta.ai/docs/structured-output | **Documented; mocked tests only** |
| `vision(image_bytes,mime,prompt,json_schema)` | Muse Spark chat multimodal message with text part plus `image_url:{url:"data:<mime>;base64,..."}` | https://dev.meta.ai/docs/api-reference/chat-completions/schemas and https://dev.meta.ai/docs/coding-agents | **Documented; mocked tests only** |
| `image(prompt,size)` | `muse-image-1.0`, OpenAI `images.generate`, response `data[0].b64_json` | https://dev.meta.ai/docs/image-generation | **Documented; mocked tests only** |
| `segment(image_bytes,mime)` | `sam-3.1` through Responses and Files; text prompt and mask extraction required | https://dev.meta.ai/docs/overview | **UNVERIFIED / NotSupported; no paid call** |
| Muse Voice transcription | `POST /v1/asr/transcribe` is documented but the full multipart schema is not verified in this PR | https://dev.meta.ai/docs/overview | **UNVERIFIED in central adapter** |

The demo mode returns `provenance="sample"`, never `live_meta`. Text budget reserves 5 cents; vision reserves 10 cents; Muse Image reserves 2 cents **before** the request. These are conservative app-local reservations, not measured charges and not account-wide limits. No refunds occur on failed calls.

The legacy `providers.py`, `media_routes.py`, `creative_routes.py` and smoke workflow require a controlled follow-up refactor; do not activate their live multimodal paths before they route through this same guard and have tests. Existing Codex PR #2 must be merged or reviewed before deploying. Schema declarations must also be validated against server-side allowed JSON Schema subsets. Image payloads should additionally undergo shared Pillow validation before public use.

Real provider response shape, model entitlement, billing, and correctness require a manual, user-authorized smoke call. Never log keys or raw image blobs.
