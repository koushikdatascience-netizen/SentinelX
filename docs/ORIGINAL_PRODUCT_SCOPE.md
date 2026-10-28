# SentinelX — Autonomous Multimodal Business Intelligence and Action Engine

**The AI that understands a business and helps run it.** The owner reaffirmed this original application scope on 28 October 2026. The campaign generator is one tool inside that product. The original scope is retained; existing history and the eligibility uncertainty are preserved.

## Five defining capabilities and their connected implementation

| Original capability | Implementation | Boundary |
| --- | --- | --- |
| Visual Business Twin | Workspace-scoped reusable product/store/document/video reviews and owner operations notes; hashed input metadata, provenance and visible unknowns. Selected context feeds both research and planning. | Model interpretation is not established business truth. Original uploads are not retained. SAM pixel segmentation is still unsupported; Muse Spark supplies visual understanding. PDF/MP4 need live-account verification separately. |
| Autonomous Opportunity Hunter | Explicitly enabled Meta web search with citations, one built-in search-call limit, bounded candidate-page retrieval through the DNS-pinned collector, researcher/planner handoff and source-quote checks. | Candidates are not automatically confirmed competitors. Search failure stops rather than fabricating sources. Partial static-page text is not a full market survey or rendered-site audit. |
| Creative Execution Studio | Existing campaign/image/document tools remain available. A selected mission opportunity can directly produce a useful landing draft and optional Muse Image concept without requiring a seven-post campaign. Context, source constraints and chosen opportunity guide the draft. | Generated concepts are not documentary product photographs. Drafting does not publish. Video scripts are text; generated video is not supported by the verified API. |
| Supervised autonomous agents | Bounded collector → hunter → researcher → planner → solution designer → optional creative → human gate → publisher → public verifier. Separate model requests, deterministic tools and human decisions are identified. Receipts persist actual execution and verification. Failed checks allow a new correction draft requiring fresh review. | This is a supervised workflow with separate contexts, not seven continuously running independent model workers. The agent cannot interpret voice, generation or a prior approval as permission for a different draft. Only self-hosted page publication is implemented; no automatic social posting. |
| Voice-to-Action | Record locally or upload WAV; Muse Voice returns an editable goal. Owner explicitly chooses to use the goal and separately starts the mission. Mission explanations can request English, Bengali or Hindi; original quote language is preserved. | Microphone is user-initiated, capped at 60 seconds and stopped on exit. Transcription is not execution approval. Sample transcription is visibly authored; runtime success, not configuration, establishes live verification. |

## One cohesive owner journey

1. Open **Business engine** from the dashboard/sidebar.
2. Add operations notes or consented product/store/document media. Review the business-twin interpretation. Optionally record/transcribe, edit and use a voice goal.
3. Choose saved context, optional cited market discovery and research/planning roles. Explicitly run the mission. Inspect source snapshots, unknowns and the real execution trace.
4. Select an opportunity and prepare an improvement, with an optional generated visual. Inspect/edit the proposed page. Approve only that exact draft.
5. Separately consent to publishing the self-hosted page and submitting/removing a labeled synthetic inquiry. Execute and inspect the machine-readable receipt.
6. If verification fails, inspect the failure, prepare a correction, and review/approve the new draft. No silent patch or republication occurs. Measure real inquiries separately.

All model requests use the central client and atomic app/workspace/run reservations before transport. Repository defaults remain demo/paid-off; guest sessions cannot invoke live generation or the new execution endpoint. Request IDs/digests reuse saved operations rather than repeating paid calls. Notes alone and reading saved results make no model calls. Each new live file context, voice transcription or solution draft uses one request; optional visual adds one; a mission uses one planner plus optional researcher/search/one citation repair. Search reserves six cents, other requests five, as application accounting units rather than reconciled provider charges.

## Evidence and unresolved scope

Implementation/HTTP-contract tests are not live-account verification. `/api/v1/status` reports recent actual voice/search/text/vision/image success; private artifacts stay owner-scoped. Backend tests cover citation/URL/audio bounds, owner isolation, deduplication, search/context handoffs, approval gating, technical delivery, replay and correction review. Browser journeys exercise the integrated controls and the local verifier's fail-closed boundary. Exact passing counts belong in release CI evidence.

Retain these original ambitions as unfinished work rather than quietly removing them: continuous scheduled opportunity monitoring, broader approved execution adapters, calibrated business-outcome measurement, general operational integrations, and pixel-accurate SAM processing. This release connects the five core capabilities in a bounded mission; it does not certify a complete production workforce or prove business uplift. The original Kamal Woodcraft production site remains unrelated infrastructure and is not modified.

Eligibility remains **UNCONFIRMED** pending organizer clarification; see [HACKATHON_CODE_PROVENANCE.md](HACKATHON_CODE_PROVENANCE.md). New product work continues on the existing repository. A fresh implementation is conditional on an explicit applicable rule, never a reason to copy or redate old code.

## Reusable source discovery

Completed live searches retain owner/workspace-scoped evidence snapshots. Owners may explicitly reuse a validated snapshot for the same business website; its original capture time and provider-results/inline-annotation distinction remain visible. Candidate pages are independently fetched again. Reuse performs no new search request and claims only the remaining research/planning quota. Sample, unvalidated, foreign-workspace or different-website evidence is rejected. Fresh search uses the business URL, goal, research focus and page title, with a concise response bound; it does not send the raw page text as the query. A failed search remains a failed run; source reuse is an explicit subsequent request, not a silent substitute.
