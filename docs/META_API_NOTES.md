# Meta Model API contract and implementation notes — 28 October 2026

The references below are official API documentation, **not a live entitlement test**. A configured key and promotional credits do not alone verify model access.

| Capability | Contract / access path | Status |
|---|---|---|
| Muse Spark text | OpenAI-compatible `chat.completions.create` at `https://api.meta.ai/v1`, `muse-spark-1.3`, `max_completion_tokens`, structured JSON `response_format` | Implemented in `MetaClient.text`; mocked tests, live usable output pending |
| Muse Spark image input | chat message with text and `image_url` data URL | Implemented in `MetaClient.vision`; live validation pending |
| Muse Image | `images.generate(model="muse-image-1.0")`, base64 image payload | Implemented in `MetaClient.image`; live validation pending |
| SAM 3.1 segmentation | Responses/Files-based pathway requires independently validated request/response and mask interpretation | **UNVERIFIED / NotSupported** for live calls |
| Muse Voice | ASR multipart request details are not centrally verified | **UNVERIFIED / live disabled** |

Sources:
- https://dev.meta.ai/docs/protocols/chat-completions
- https://dev.meta.ai/docs/structured-output
- https://dev.meta.ai/docs/api-reference/chat-completions/schemas
- https://dev.meta.ai/docs/image-generation
- https://dev.meta.ai/docs/overview
- https://dev.meta.ai/docs/reasoning

Safety:
- All current hosted Meta text and image calls route through `MetaClient`; old direct legacy inference is disabled; unverified live voice fails closed.
- `INFERENCE_PROVIDER=meta`, `SENTINELX_MODE=live`, `ALLOW_PAID_INFERENCE=true` and `ENABLE_LIVE_MULTIMODAL=true` must all be enabled for any live Meta operation, plus valid `MODEL_API_KEY`.
- Budget reservations are made before each paid request (text $0.05, vision $0.10, image $0.02 conservative application reservations), with no automatic retries. This is not the Meta account balance or a guaranteed provider hard cap.
- Campaigns, product vision, and creatives require a positive per-workspace attempt ceiling, `CAMPAIGN_WORKSPACE_MAX_ATTEMPTS`. Current quota is lifetime per workspace, not per-day. The same budget applies across operations.
- `/api/v1/status` shows LIVE only after recent real successful SDK calls recorded by this application; CI SDK mocks never count. Ephemeral GitHub smoke jobs record state in disposable SQLite and do not update a separate deployed server.
- Deterministic samples return `provenance: sample`; claims derived from owner submissions remain unverified even if repeated by a model.
- The central adapter returns a schema-shaped object but the consuming route must also validate returned objects via Pydantic. Exact supported JSON Schema subset, account entitlements and actual billed usage still require live testing.

No paid requests were authorized or executed by this PR.
