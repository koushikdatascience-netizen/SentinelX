# SentinelX Indie submission plan

> Historical setup/planning notes. For current live verification, judge access, quotas and implemented capabilities, read [DEMO_READINESS.md](DEMO_READINESS.md). The old empty smoke response and early scaffold limitations are not the current product state.

Reviewed October 27, 2026. User confirms Indie developer track.

## Positioning

Proposed pitch: **SentinelX turns an artisan business owner's scattered evidence into a traceable growth experiment the owner controls.**

Start with a furniture maker's concrete workflow. Broad autonomous business intelligence is difficult to demonstrate credibly within the remaining build window. A complete evidence-to-draft journey is the recommended differentiation; seven simulated agents are a development preview, not the main proof.

## Verified competition facts and unknowns

The [official Meta event page](https://dev.meta.ai/events/global-hackathon) describes a $1M total pool across two tracks, with one track per project. Indie entries emphasize creativity, technical ambition and working behavior. Build for Your World is the recommended theme for this domain-specific workflow. The published submission deadline is November 4 at 9 PM ET, which converts to **November 5, 2026 at 7:30 AM IST**. Recheck the portal for changes; aim to submit November 4 IST.

The [organizer page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) lists conditional partner credits: Baseten $100, Modal $100 and Fireworks $25 for selected participants. These are not cash awards or guaranteed allocations.

The public [waiver page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver) did not expose readable rules during this review. Detailed prize amounts, bonus categories, stacking permissions, judging weights, pre-existing-code restrictions, video length and submission fields remain unverified. Do not claim the previously mentioned $10k open-weight award as confirmed. Obtain the accepted participant rules before spending time to target a bonus category. Disclose the pre-existing scaffold and work completed during the event accurately.

## Delivery order and acceptance evidence

| Priority | Deliverable | Evidence needed before claiming completion |
| --- | --- | --- |
| P0 | Complete visible Meta text response | One manually gated request after mock checks; nonempty text, stop finish reason, safe usage metadata, no retry |
| P0 | Owner evidence to usable draft | Authenticated, owner-scoped run containing supplied evidence and a model-generated homepage/quotation draft; separate observed facts from assumptions |
| P0 | Browser journey | Register allowed test user, create workspace, supply excerpt, inspect result, propose/review action and export report; verify second user cannot access it |
| P0 | Stable isolated demo | HTTPS and health checks if deployed, tested setup instructions, no production-site changes, explicit replay fallback label |
| P1 | One useful multimodal step | Consented product photo or voice note contributes to the actual draft; real model ID, source reference and consent visible. File validation alone is not inference |
| P1 | Real-user usefulness check | Owner times the manual task and assisted task, reviews drafts against a written rubric and records feedback with permission; do not infer revenue impact |
| P1 | Small reproducible evaluation | At least 10 self-authored/consented fixtures: missing facts, prompt injection, conflicting claims, truncation and cross-owner access; report sample size and failures |
| Conditional | Open-weight integration | Only if eligibility is confirmed: real Muse Glimmer or Spark Open inference, exact provider/model evidence and a measured role such as extracting facts or checking a draft |

Do not add image, voice or segmentation solely to increase a model count. Choose one input that changes the owner's result. Do not fine-tune, build a general crawler or add external publishing before the core journey is reliable.

## Suggested work calendar (IST)

- Oct 27–28: publish tested fixes for review; validate visible text once; confirm accepted rules and permitted use of pre-existing code.
- Oct 29–30: implement model-backed evidence-to-draft flow and complete browser journey; retain deterministic demo fallback with explicit labels.
- Oct 31–Nov 1: one consented multimodal input, small evaluation and owner feedback. Pursue open weights only if rules and core readiness justify it.
- Nov 2: isolated staging and reliability pass; record setup and operational limits.
- Nov 3: record and rehearse demo, verify submission fields and attribution.
- Nov 4: freeze features, submit early and verify submitted links from another browser/session.

## Credit discipline

No Meta calls were made for this strategy review. Use mocks for development, save sanitized fixed-fixture outputs for explicitly labeled replay, and keep live inference opt-in. Never replay one owner's content to another owner. A proposed operating target is at most $5 of development credit consumption before reassessing quality; this is a planning target, not an enforced provider cap. Preserve the remaining credits for meaningful evaluation and the final demo. Run one bounded request after each justified adapter change, not after every UI edit. Do not repeatedly rerun empty responses. Count reasoning tokens as output; actual charges need provider reconciliation.

## Proposed two-minute demo (confirm portal length first)

- 0:00–0:15: show the artisan's specific task and existing source material.
- 0:15–0:40: supply authorized excerpt and, if implemented, consented media; show provenance and model mode.
- 0:40–1:10: generate a useful draft; inspect one supported fact and one explicitly unknown fact.
- 1:10–1:30: edit/review a proposed action and export the artifact; explain approval records a decision.
- 1:30–1:50: show measured evaluation and owner feedback, including a failure case.
- 1:50–2:00: show architecture and next experiment; distinguish live inference, deterministic processing and recorded replay.

Suggested submission attachments: working demo URL/setup, short video, architecture diagram, test output, evaluation with sample count, sanitized model provenance, credit usage summary and a limitations statement. This list is a preparation recommendation, not verified portal requirements.

## Participant-guide update supplied 28 October 2026

The owner supplied the event Participant Guide and organizer announcements. See [HACKATHON_CODE_PROVENANCE.md](HACKATHON_CODE_PROVENANCE.md) for attachment hashes, source limitations, the 54 recorded pre-kickoff commits and the indie-track eligibility concern. **Eligibility remains UNCONFIRMED.** The guide requires new work, a public repository and a three-minute demo; its explicit existing-codebase exception is stated for startups and must not be assumed to cover indie entries. The guide lists simple image analyzers among anti-project examples. Do not position SentinelX as only an image analyzer or a generic chatbot.

The guide supplies the judging weights: Impact 30%, Meta tooling 25%, Technical depth/execution 20%, Demo 25%. It lists indie prizes of $150K/$100K/$75K/$50K/$25K and bonus awards for viral project ($20K), eligible Meta open-weight build ($10K), community vote ($10K), agentic use case ($5K), and creative build ($5K). Prize stacking is not established by that list. Open-weight bonus eligibility needs an actual eligible model deployment and partner verification; a model name in code is not sufficient.

The guide says building period 27 October–4 November, kickoff 26 October noon Eastern, and submission 4 November 9 PM Eastern. The EST/ET naming inconsistency and exact allowed coding-start rule require clarification. Use the updated [three-minute script](DEMO_SCRIPT.md); the earlier two-minute planning section is superseded. Do not add unrelated model integrations merely to target a bonus. Prioritize verified usefulness, the coherent source-to-action demo and truthful attribution.
