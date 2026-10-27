# Meta API contracts and verification notes

Reviewed October 28, 2026. **Documentation-verified and mock-tested does not mean live-account verified.** No paid request was made during this change. The earlier smoke received usage and empty text; it does not certify useful output or multimodal access.

## Contracts implemented in app/meta_client.py

| Capability | Official contract | Client behavior |
| --- | --- | --- |
| Text | `POST https://api.meta.ai/v1/chat/completions`, `muse-spark-1.3`, Bearer MODEL_API_KEY; developer/user messages; visible text in `choices[0].message.content` | Fixed supported model; minimal reasoning; 500 combined output tokens by default (constructor 1–6000). Empty text or non-stop finish fails. |
| Structured text | Chat Completions `response_format={type:json_schema,json_schema:{name,schema,strict}}` | Uses strict=false for broader schema compatibility, plus local Draft 2020-12 validation. Nonrecursive local Pydantic `$defs` are inlined before sending; remote and recursive references are rejected without a call. Invalid/oversized schemas fail before reservations. |
| Vision | Same model and endpoint; user content contains `text` and `image_url` blocks, with `image_url.url` holding a base64 data URL | Sends local validated PNG/JPEG/WebP only, up to 5 MB / 20MP. No URL fetching. Optional schema uses the same validation. |
| Image | `POST /v1/images/generations`, `muse-image-1.0`, prompt, n, size, response_format; output `data[].b64_json` or signed URL | One image, three allowlisted aspect ratios, base64 output. Size is an aspect ratio, not a promise of exact dimensions. No automatic edits, downloads, retries or publishing. |
| SAM | `sam-3.1` on Responses API, object concept/geometry prompt and media; special-token segmentation output | **UNVERIFIED / NOT IMPLEMENTED adapter.** API exists, but this method has no object prompt argument and the mask parser is not integrated. Live `segment` raises NotSupported before budget/network. Never substitutes vision text for a mask. |
| Voice | Old hand-written ASR request removed | **UNVERIFIED adapter.** Live transcription raises NotSupported. Offline intake returns transcript=null with sample provenance; never claims speech recognition. |

Official sources:

- [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions)
- [Structured output](https://dev.meta.ai/docs/structured-output)
- [Image understanding](https://dev.meta.ai/docs/image-understanding)
- [Image generation](https://dev.meta.ai/docs/image-generation)
- [Reasoning](https://dev.meta.ai/docs/reasoning): hidden reasoning counts against output limits and billed output; minimal is supported, none is not.
- [Media segmentation](https://dev.meta.ai/docs/media-segmentation)
- [SAM client libraries](https://dev.meta.ai/docs/sam/client-libraries): special-token parsing needs a dedicated parser.

## Gates, scope and accounting

Every MetaClient method checks INFERENCE_PROVIDER (default demo), ALLOW_PAID_INFERENCE (default false) and ENABLE_LIVE_MULTIMODAL (default false). **Both boolean flags must be true even for text.** Disabled flags return deterministic sample fixtures without constructing an SDK client or reserving credits. No schema fixture is invented as real intelligence; unsupported fixture schemas fail explicitly. SAMPLE_PNG is an authored tiny fixture, not a model image.

Live calls require MODEL_API_KEY from environment, an owner ID, an existing owned workspace and an existing run in that workspace. Budget checks revalidate ownership in the database, not merely in route parameters. Scoped routes check ownership before processing model input, even in sample mode. Existing stateless local inspection/intake routes keep their authenticated no-storage behavior; they cannot access another owner's records. Live unscoped text requests fail closed. Legacy paid analyze is removed.

`budget.reserve_meta` atomically reserves 5 cents in all three counters in one transaction: META_APP_BUDGET_CENTS (existing default 500), META_WORKSPACE_BUDGET_CENTS (default **0**) and META_RUN_BUDGET_CENTS (default **0**). Workspace/run counters use hashed keys in the existing api_budgets table, so no new migration is required. Five cents is an application reservation unit, **not a verified price or guaranteed maximum charge**. Counters are lifetime cumulative; there is no automatic reset or refund after uncertain failures. Concurrent calls serialize on the global row; insufficient scope rolls back every debit. Provider charge reconciliation remains unimplemented. Other apps, keys and workflow dispatches bypass this application's shared DB accounting.

SDK transport uses a 90-second timeout, max_retries=0 and safe fixed error messages. Keys, full prompts, provider error bodies, hidden reasoning and generated media are not logged. Only whitelisted usage fields leave the text adapter. All enabled hosted model traffic delegates to MetaClient.

## Manual smoke verification

The workflow remains manual, protected by meta-live-test and the exact acknowledgement `I_ACKNOWLEDGE_ONE_PAID_REQUEST`. Choose **one** of text, vision or image per dispatch. There is no all-capabilities mode or matrix. It uses an ephemeral dedicated SQLite accounting DB with app/workspace/run caps of 5 cents, creates a synthetic owner/run, then makes one method call. Text/vision have a 128-token combined limit; image generates one image. Logs print only capability, provenance, model, output-presence and numeric usage, never response text/base64. Samples cannot pass as a live smoke success.

Each dispatch has its own accounting DB, so it is not a cross-dispatch billing cap. Do not dispatch repeatedly after a failure. The operator must inspect safe diagnostics and provider billing. Updating the workflow does not enable the app, change deployed configuration or authorize an actual smoke run.

## Status

Documentation and mocked HTTP shapes: text, structured output, vision, single-image generation. Live-account success, model entitlement, useful output quality and actual cost reconciliation: **UNVERIFIED**. SAM/voice live adapters: explicitly unsupported. Defaults remain demo/paid-off. Hostinger staging has been audited; the CD workflow is prepared but remains disabled pending merge and restricted deployment credentials. See [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md).


### Compatibility changes

`POST /api/v1/creative/generate` now requires workspace_id and run_id in its JSON body. `POST /api/v1/media/image/analyze` requires those IDs as query parameters plus an uploaded file; prompt is optional. Both check the authenticated owner before invoking the client, including samples. `/api/v1/inference/test` accepts optional scope fields for backward-compatible stateless samples, but live Meta inference cannot proceed without a persisted owned run. Workspace generation creates that run before attempting inference. Existing voice intake accepts local sample files only; its old unmetered live HTTP path is gone. All approval endpoints remain recorded decisions only.

## Live Studio integration repair

Campaign generation uses one structured request containing the audit and seven-day plan, bounded to 6,000 output tokens. The original nested Pydantic schemas could not pass the client; local definitions are now expanded safely and covered by an HTTP transport test. Owner requests explicitly choose live generation and receive an error rather than a sample substitution when unavailable. Guest sessions and the explicit sample checkbox remain sample-only.

The Hostinger workflow transfers the owner-configured MODEL_API_KEY over pinned SSH into the root-only server env file; it is never committed or uploaded as a workflow artifact. A live activation starts with $2 in cumulative app/workspace reservations, a 50-cent run limit, and 20 attempts per workspace. These are application reservations rather than provider billing reconciliation. No request is made merely by deploying.
