# Meta API contracts and verification notes

Reviewed October 28, 2026. **Documentation-verified and mock-tested does not mean live-account verified.** The deployed owner workflow was verified with four real requests on 28 October 2026: campaign text, image generation, image-input assessment and landing text. See DEMO_READINESS.md for stored artifact IDs and test evidence.

## Contracts implemented in app/meta_client.py

| Capability | Official contract | Client behavior |
| --- | --- | --- |
| Text | `POST https://api.meta.ai/v1/chat/completions`, `muse-spark-1.3`, Bearer MODEL_API_KEY; developer/user messages; visible text in `choices[0].message.content` | Fixed supported model; minimal reasoning; 500 combined output tokens by default (constructor 1–6000). Empty text or non-stop finish fails. |
| Structured text | Chat Completions `response_format={type:json_schema,json_schema:{name,schema,strict}}` | Uses strict=false for broader schema compatibility, plus local Draft 2020-12 validation. Nonrecursive local Pydantic `$defs` are inlined before sending; remote and recursive references are rejected without a call. Invalid/oversized schemas fail before reservations. |
| Vision | Same model and endpoint; user content contains `text` and `image_url` blocks, with `image_url.url` holding a base64 data URL | Sends local validated PNG/JPEG/WebP only, up to 5 MB / 20MP. No URL fetching. Optional schema uses the same validation. |
| Image | `POST /v1/images/generations`, `muse-image-1.0`, prompt, n, size, response_format; output `data[].b64_json` or signed URL | One image, three allowlisted aspect ratios, base64 output. Size is an aspect ratio, not a promise of exact dimensions. No automatic edits, downloads, retries or publishing. |
| SAM | `sam-3.1` on Responses API, object concept/geometry prompt and media; special-token segmentation output | **UNVERIFIED / NOT IMPLEMENTED adapter.** API exists, but this method has no object prompt argument and the mask parser is not integrated. Live `segment` raises NotSupported before budget/network. Never substitutes vision text for a mask. |
| Voice | `POST /v1/asr/transcribe`; multipart `request` JSON with `model=muse-voice-transcribe-1.0`, `audioEncoding=WAV`, `mode=PUSH_TO_TALK`; `audio` is mono 16-bit WAV at 16/24 kHz; JSON returns `transcript`, `audioDurationMs`, `turns` | Scoped SDK generic POST, 90-second timeout/retries=0. Local validation limits clips to 60 seconds before charging. Sample transcript is authored and labeled. Runtime success establishes account verification. |
| Search | Responses `muse-spark-1.3`, `tools=[{type:web_search,search_context_size:low}]`, `include=[web_search_call.results]`, `max_tool_calls=1` | Requires completed response, one completed search, bounded text and usable public sources. Distinguishes valid inline URL annotations from provider search-result links. No live-to-sample fallback. |

**Observed account behavior, 28 October:** an actual completed search returned nine raw results and visible output with empty annotation arrays. The documentation's annotation example was not the observed format. The client now reports `citation_mode=provider_results`, `has_inline_citations=false` and null span indices in that case. These links are documented `web_search_call.results` evidence pointers, never invented URL annotations or proof that each summary claim is supported. The mission independently retrieves candidate pages and checks report quotes against those collected snapshots. Malformed supplied annotations, no actual search, empty/incomplete text or neither annotations nor usable result links still fail closed. The initial failure and one diagnostic request were not automatically retried; existing successful voice/image artifacts are reused.

Official sources:

- [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions)
- [Structured output](https://dev.meta.ai/docs/structured-output)
- [Image understanding](https://dev.meta.ai/docs/image-understanding)
- [Image generation](https://dev.meta.ai/docs/image-generation)
- [Reasoning](https://dev.meta.ai/docs/reasoning): hidden reasoning counts against output limits and billed output; minimal is supported, none is not.
- [Media segmentation](https://dev.meta.ai/docs/media-segmentation)
- [SAM client libraries](https://dev.meta.ai/docs/sam/client-libraries): special-token parsing needs a dedicated parser.
- [Search grounding](https://dev.meta.ai/docs/search-grounding), [Responses schemas](https://dev.meta.ai/docs/api-reference/responses/schemas), [tool-call limits](https://dev.meta.ai/docs/tool-calling).
- [Recorded transcription](https://dev.meta.ai/docs/api-reference/voice/transcribe), [voice schemas](https://dev.meta.ai/docs/api-reference/voice/schemas), [WAV and language support](https://dev.meta.ai/docs/speech-to-text).

## Gates, scope and accounting

Every MetaClient method checks INFERENCE_PROVIDER (default demo), ALLOW_PAID_INFERENCE (default false) and ENABLE_LIVE_MULTIMODAL (default false). **Both boolean flags must be true even for text.** Disabled flags return deterministic sample fixtures without constructing an SDK client or reserving credits. No schema fixture is invented as real intelligence; unsupported fixture schemas fail explicitly. SAMPLE_PNG is an authored tiny fixture, not a model image.

Live calls require MODEL_API_KEY from environment, an owner ID, an existing owned workspace and an existing run in that workspace. Budget checks revalidate ownership in the database, not merely in route parameters. Scoped routes check ownership before processing model input, even in sample mode. Existing stateless local inspection/intake routes keep their authenticated no-storage behavior; they cannot access another owner's records. Live unscoped text requests fail closed. Legacy paid analyze is removed.

`budget.reserve_meta` atomically reserves 5 cents (6 cents for search) in all three counters in one transaction: META_APP_BUDGET_CENTS (existing default 500), META_WORKSPACE_BUDGET_CENTS (default **0**) and META_RUN_BUDGET_CENTS (default **0**). Workspace/run counters use hashed keys in the existing api_budgets table, so no new migration is required. Five cents is an application reservation unit, **not a verified price or guaranteed maximum charge**. Counters are lifetime cumulative; there is no automatic reset or refund after uncertain failures. Concurrent calls serialize on the global row; insufficient scope rolls back every debit. Provider charge reconciliation remains unimplemented. Other apps, keys and workflow dispatches bypass this application's shared DB accounting.

SDK transport uses a 90-second timeout, max_retries=0 and safe fixed error messages. Keys, full prompts, provider error bodies, hidden reasoning and generated media are not logged. Only whitelisted usage fields leave the text adapter. All enabled hosted model traffic delegates to MetaClient.

## Manual smoke verification

The workflow remains manual, protected by meta-live-test and the exact acknowledgement `I_ACKNOWLEDGE_ONE_PAID_REQUEST`. Choose **one** of text, vision or image per dispatch. There is no all-capabilities mode or matrix. It uses an ephemeral dedicated SQLite accounting DB with app/workspace/run caps of 5 cents, creates a synthetic owner/run, then makes one method call. Text/vision have a 128-token combined limit; image generates one image. Logs print only capability, provenance, model, output-presence and numeric usage, never response text/base64. Samples cannot pass as a live smoke success.

Each dispatch has its own accounting DB, so it is not a cross-dispatch billing cap. Do not dispatch repeatedly after a failure. The operator must inspect safe diagnostics and provider billing. Updating the workflow does not enable the app, change deployed configuration or authorize an actual smoke run.

## Status

Documentation and mocked HTTP shapes: text, structured output, vision, single-image generation. Live-account text, structured output, vision and image generation: **VERIFIED on Hostinger**. Actual provider cost reconciliation remains unimplemented. SAM/voice live adapters: explicitly unsupported. Defaults remain demo/paid-off. Hostinger CI/CD is active and the owner explicitly enabled bounded live inference using the production environment secret. See [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md).


### Compatibility changes

`POST /api/v1/creative/generate` now requires workspace_id and run_id in its JSON body. `POST /api/v1/media/image/analyze` requires those IDs as query parameters plus an uploaded file; prompt is optional. Both check the authenticated owner before invoking the client, including samples. `/api/v1/inference/test` accepts optional scope fields for backward-compatible stateless samples, but live Meta inference cannot proceed without a persisted owned run. Workspace generation creates that run before attempting inference. Existing voice intake accepts local sample files only; its old unmetered live HTTP path is gone. All approval endpoints remain recorded decisions only.

## Live Studio integration repair

Campaign generation uses one structured request containing the audit and seven-day plan, bounded to 6,000 output tokens. The original nested Pydantic schemas could not pass the client; local definitions are now expanded safely and covered by an HTTP transport test. Owner requests explicitly choose live generation and receive an error rather than a sample substitution when unavailable. Guest sessions and the explicit sample checkbox remain sample-only.

The Hostinger workflow transfers the owner-configured MODEL_API_KEY over pinned SSH into the root-only server env file; it is never committed or uploaded as a workflow artifact. A live activation starts with $2 in cumulative app/workspace reservations, a 50-cent run limit, and 20 attempts per workspace. These are application reservations rather than provider billing reconciliation. No request is made merely by deploying.

## Website reports and attached media (28 October 2026)

[Models](https://dev.meta.ai/docs/models) distinguishes input from output: Muse Spark reads text, images, video, audio and PDFs and returns text; Muse Image generates images. No public video-generation endpoint was verified. Shooting scripts are text documents, never rendered videos.

`MetaClient.review_media` reuses budgeted image vision. For MP4/PDF it sends one `POST /v1/responses` request to `muse-spark-1.3`, `store=false`, minimal reasoning, a bounded output limit and no retries. MP4 uses `input_video` with an inline base64 `video_url`; PDF uses `input_file` with filename and inline `file_data`. Only completed nonempty `output_text` is accepted. The app limits files to 5 MB and checks containers; it does not locally decode video or parse PDF pages.

Contracts: [Video understanding](https://dev.meta.ai/docs/video-understanding), [File handling](https://dev.meta.ai/docs/file-handling), [Responses API](https://dev.meta.ai/docs/protocols/responses). Video audio support has documented quality limitations. PDF/MP4 adapters are **documentation-verified and mocked HTTP-tested, not live-account verified**. Image input retains prior live verification. Owner isolation, consent, quotas and app/workspace/run budget reservations precede transport. Original bytes are not saved by SentinelX; inline requests create no provider Files resource.

Website media references are inventoried, not silently downloaded or visually assessed. Owners explicitly upload media for separate reviews. New report plans include source-quoted strengths, existing feature coverage, justified changes, priorities and inspection limitations. Older saved reports retain their original contents.

Business briefs, inquiry checklists and shooting scripts use separate explicit text requests. Downloads are Markdown or autoescaped printable HTML. Binary PDF/DOCX creation is not implemented. Report exports include attached saved media reviews/documents. Opening saved content or deploying never triggers a paid request. Campaign creation and page publication remain optional follow-ups.

## Citation repair update

Whitespace and equivalent Unicode quotation marks/dashes normalize before source matching in website reports and the older evidence-draft validator. Words, case, numbers and negation remain significant; arbitrary fuzzy matches are not accepted. Website reports offer an opt-in `allow_quote_repair` control, default false. Only a citation mismatch after a completed structured response can trigger at most one extra model call. It claims another workspace attempt and reserves the same app/workspace/run budgets before HTTP; a budget denial causes no second transport request. The corrected report must pass the same schema/source checks. Network/schema/incomplete-response failures are not retried. Manual smoke remains one call, SDK max_retries=0. No paid call was needed to test this behavior.

## Observed search evidence reuse

The context-rich mission search stopped twice. A targeted live request subsequently completed and its nine documented `text_result` records (title, URL and snippet) validated in provider-results mode. That visible source evidence is retained as a private, validated snapshot, without keys, request headers or hidden reasoning. The mission can explicitly reuse such a snapshot for the same owned workspace and business website, disclose its capture time, and independently fetch candidate pages. No fresh-search or inline-span claim is made for reuse. Fresh requests are bounded to a concise source-discovery answer; safe validation failures now appear in the saved trace. Image/voice outputs are reused rather than generated again.
