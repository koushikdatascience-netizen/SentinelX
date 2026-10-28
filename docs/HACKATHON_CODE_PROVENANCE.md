# SentinelX hackathon code provenance

**Eligibility: UNCONFIRMED.** Audited 28 October 2026 (IST). This is a factual code-history record, not an organizer decision or legal eligibility assessment. No history has been rewritten.

## Sources and scope

Source snapshot: `d25d23b946d60b43b4ae3ac21deb6e13428ebc34`. Remote main was fetched; `git rev-parse --is-shallow-repository` returned **false**. `git log --all` covers 257 commits reachable from the locally available refs, with one root. It cannot establish missing/deleted branches, earlier source authored outside Git, or work imported with later timestamps.

Public sources: [Meta event page](https://dev.meta.ai/events/global-hackathon), [organizer listing](https://events.cerebralvalley.ai/e/meta-ai-developer-hackathon), [participant details URL](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details). The details URL returned a loading shell to the browser fetch; the guide text below comes from the owner's pasted participant materials and has not been independently authenticated in full.

- Participant Guide, supplied by owner on 28 October 2026: SHA-256 `da364a05aadd6c534b781ed9cd76e9f04206f84d790421ab90ce8555e5d7af24`.
- Event listing and announcements, supplied by owner on 28 October 2026: SHA-256 `bce4c35d79539f77da67cdf7e6f4607fc0b38f31873b0e6a0b8ee6f27223e4f0`.

The supplied guide says “New work only” and limits demos to features built during the event. It explicitly mentions startups building on existing codebases with clear new-work identification. It does **not** explicitly extend that exception to indie entrants. Do not assume permission or disqualification: ask organizers how the indie entry may use/disclose the earlier scaffold.

## Earliest history and start-boundary ambiguity

Root: [`1075a84aab6ae1fc802a35584e3549000b3d1d32`](https://github.com/koushikdatascience-netizen/SentinelX/commit/1075a84aab6ae1fc802a35584e3549000b3d1d32), author and committer date **26 October 2026, 14:40:00 +05:30**. Its only file is `README.md` with seven inserted lines. Backend and frontend code arrives in subsequent commits; the root itself is not an application scaffold.

The supplied guide lists kickoff at **26 October, 12:00 PM Eastern** and a **building period of 27 October–4 November**. Some supplied/public labels say EST while the schedule says ET. On 26 October New York observes UTC−04:00 (12:00 ET = 21:30 IST); literal UTC−05:00 EST gives 22:30 IST. Neither should be silently substituted for an official allowed coding-start rule. The distinction does not alter the earliest scaffold's classification: its recorded dates precede both kickoff interpretations.

| Search boundary (not an eligibility rule) | ISO instant | Earlier author dates | Earlier committer dates |
| --- | --- | --- | --- |
| calendar_midnight_IST | 2026-10-26T00:00:00+05:30 | 0 | 0 |
| kickoff_ET_EDT | 2026-10-26T12:00:00-04:00 | 54 | 54 |
| kickoff_literal_EST | 2026-10-26T12:00:00-05:00 | 54 | 54 |
| building_period_Oct27_ET | 2026-10-27T00:00:00-04:00 | 54 | 54 |

Zero commits before 26 October midnight is **not** zero pre-kickoff work. The initial code foundations recorded on 26 October are pre-kickoff under both interpretations above. The exact allowed work window and whether the guide's 27 October building-period label is controlling require clarification.

## Categories to disclose

| Category | Repository evidence | Required treatment |
| --- | --- | --- |
| Pre-kickoff recorded SentinelX code | 26 October foundations below, before either noon-Eastern kickoff interpretation | Disclose as pre-kickoff scaffold. Do not present as newly built during the hackathon. Exact original authoring dates still need owner confirmation. |
| Code written before its recorded commit | Git cannot determine this; owner previously described an existing scaffold | **UNCONFIRMED.** Identify imports/prior work from actual development records; a later commit timestamp does not cure pre-existing authorship. |
| Recorded event/build-period development | 27–28 October features below | Diff-verifiable implementation changes. Claim as during-event work only when owner authoring records and official window support that statement. |
| Reusable dependencies | Requirements, package manifests/lock, containers and CI actions | Third-party frameworks/services, not original SentinelX technology. |
| Business content and infrastructure | Existing Kamal Woodcraft site, business assets, Hostinger/other existing services | External context/reused assets; no claim these were newly created for the hackathon. |
| Model outputs and fixtures | `live_meta`, `sample`, `user_supplied` labels | Distinguish actual inference, authored samples and user inputs; do not relabel fixtures. |
| Coding assistance | Codex work in this chat and owner-reported ChatGPT development | Disclose assistance as required; Git is not a complete AI-assistance ledger. |

## Feature changes, recorded dates and hashes

Each source path was checked to exist at the cited revision. Broad commit subjects are not accepted as evidence of every claimed feature: inspect the linked diff and inherited tree. All dates below are recorded author dates; full author **and committer** dates are in [provenance/commit-history.csv](provenance/commit-history.csv).

| Change | Commit | Recorded date | Relevant file at revision | Classification / technical boundary |
| --- | --- | --- | --- | --- |
| Initial repository | [1075a84](https://github.com/koushikdatascience-netizen/SentinelX/commit/1075a84aab6ae1fc802a35584e3549000b3d1d32) | 2026-10-26T14:40:00+05:30 | README.md | Before both listed kickoff interpretations. Seven-line README; no app code. |
| Scaffold file batch begins | [1cb6470](https://github.com/koushikdatascience-netizen/SentinelX/commit/1cb64702e2bfb574f0cc0c6c5e14572276fa0820) | 2026-10-26T14:40:29+05:30 | .gitignore | Before both listed kickoff interpretations. This particular commit adds .gitignore, despite its broad feature title. |
| Workflow primitive | [c5b2fb6](https://github.com/koushikdatascience-netizen/SentinelX/commit/c5b2fb6883eaae734e8ec8865b008e69e64e3281) | 2026-10-26T14:40:44+05:30 | backend/app/workflows.py | Before both listed kickoff interpretations. Deterministic action state machine. |
| Analysis/research/approval prototypes | [0911143](https://github.com/koushikdatascience-netizen/SentinelX/commit/091114394b2f302e37643061714fa57f6b8f8478) | 2026-10-26T14:41:20+05:30 | backend/app/main.py | Before both listed kickoff interpretations. Legacy prototypes; later disabled by default. |
| Mock multimodal workflow | [9330095](https://github.com/koushikdatascience-netizen/SentinelX/commit/93300950107ec8dec528f46748baf01a10dff6ef) | 2026-10-26T16:29:49+05:30 | backend/app/orchestrator.py | Before both listed kickoff interpretations. Explicit simulation, not real model execution. |
| Persistent workspace foundations | [2693c5c](https://github.com/koushikdatascience-netizen/SentinelX/commit/2693c5ca89026653fc626341b9e869a8646db4d3) | 2026-10-26T16:34:39+05:30 | backend/app/workspace_store.py | Before both listed kickoff interpretations. Auth/data foundations; not a verified live Meta integration. |
| Evidence drafts | [bac763c](https://github.com/koushikdatascience-netizen/SentinelX/commit/bac763c2056738f88d74ca9e879a9e15098ce0a8) | 2026-10-27T22:50:52+05:30 | backend/app/evidence_drafts.py | Recorded during listed event/build dates; eligibility unconfirmed. Pasted-excerpt flow and browser/migration work. |
| Central Meta client | [bdf2524](https://github.com/koushikdatascience-netizen/SentinelX/commit/bdf252440a198a5488971df4a685d2017613c72b) | 2026-10-28T00:05:37+05:30 | backend/app/meta_client.py | Recorded during listed event/build dates; eligibility unconfirmed. Documentation/contracts and mocked requests, before live certification. |
| Photo assessment | [9185089](https://github.com/koushikdatascience-netizen/SentinelX/commit/9185089232685fe801326ef8693292759e7a7eee) | 2026-10-28T00:15:57+05:30 | backend/app/image_routes.py | Recorded during listed event/build dates; eligibility unconfirmed. Local pixel metrics and optional scoped vision. |
| Seven-day campaigns | [176e40d](https://github.com/koushikdatascience-netizen/SentinelX/commit/176e40df3f288ed38d71141f5dde31c6bcecbe4c) | 2026-10-28T00:20:18+05:30 | backend/app/campaign_routes.py | Recorded during listed event/build dates; eligibility unconfirmed. Persistent localized campaign plans. |
| Landing drafts/previews/leads | [27505c1](https://github.com/koushikdatascience-netizen/SentinelX/commit/27505c110940ce951a568d5d7548b507537b9fe3) | 2026-10-28T00:23:47+05:30 | backend/app/landing_routes.py | Recorded during listed event/build dates; eligibility unconfirmed. Safe templates and consented inquiry intake. |
| Creative variants | [d7499f4](https://github.com/koushikdatascience-netizen/SentinelX/commit/d7499f4abcaa571d937a233065922c6b5902438e) | 2026-10-28T00:29:59+05:30 | backend/app/creatives.py | Recorded during listed event/build dates; eligibility unconfirmed. Sample/Meta variants and owner selection. |
| No-login sample sessions | [52e8358](https://github.com/koushikdatascience-netizen/SentinelX/commit/52e8358fd0ec35ee986f75fabab1fb7b25662692) | 2026-10-28T00:37:38+05:30 | backend/app/demo_routes.py | Recorded during listed event/build dates; eligibility unconfirmed. Short-lived isolated guest workspace; paid generation blocked. |
| Live Studio release, PR #10 | [a232170](https://github.com/koushikdatascience-netizen/SentinelX/commit/a23217066465b06b2f6d96504fdbf17e9f6759ff) | 2026-10-28T04:00:48+05:30 | backend/app/meta_client.py | Recorded during listed event/build dates; eligibility unconfirmed. Merged live-integration fixes; verification records separately listed. |
| Unified dashboard | [1d36a4c](https://github.com/koushikdatascience-netizen/SentinelX/commit/1d36a4c0557fcbe40d9df99b5be663f7a44a1eac) | 2026-10-28T04:49:00+05:30 | frontend/app/page.tsx | Recorded during listed event/build dates; eligibility unconfirmed. Dedicated tools and modal editors. |
| Source-backed mission loop | [9eb567d](https://github.com/koushikdatascience-netizen/SentinelX/commit/9eb567d9315329ed5b11a94ff7d99a1dd9f1581a) | 2026-10-28T05:27:03+05:30 | backend/app/mission_routes.py | Recorded during listed event/build dates; eligibility unconfirmed. Actual tool/model trace and technical delivery verification. |
| Balanced reports/media/documents | [1a3bc54](https://github.com/koushikdatascience-netizen/SentinelX/commit/1a3bc5469997e0872adf474fafc0a2df223b9c5c) | 2026-10-28T05:56:56+05:30 | backend/app/mission_assets.py | Recorded during listed event/build dates; eligibility unconfirmed. MP4/PDF documented/mock-tested, not live-account verified. |

The CSV snapshots existing reachable history before this new documentation commit. It intentionally cannot include its own future commit hash. New provenance/citation fixes in the current working branch must be listed by their eventual normal commit, not assigned a manufactured earlier date.

## Implementation versus successful Meta inference

A model adapter or smoke request is not proof of a useful response. The early smoke response with usage but empty text remains an earlier unsuccessful usefulness check. Subsequent owner-isolated artifacts on 28 October provide real nonempty evidence:

- Campaign `0539ada8-b38e-4b9a-b352-5e247e53d120`: Muse Spark audit/seven posts.
- Creative `8f6a6a21-6db6-47f8-9478-f1d4ea4dd659`: Muse Image, 1600 × 1600 WebP, and separate Muse Spark image-input assessment.
- Landing draft `e35ab857-c318-41fa-b8f7-588703fec0a9`: Muse Spark text and authenticated preview.
- Website report `da0475fe-a137-40ea-90ad-bc7d4885c614`: retrieved public-source evidence, exact source quotes, strengths/changes and coverage limits.

Recent successful capability timestamps/model IDs are exposed by `/api/v1/status`; active release by `/health`. CI/deployment links and limits are in [DEMO_READINESS.md](DEMO_READINESS.md). Stored outputs support technical verification; they do not establish business impact or timing eligibility. PDF/MP4 adapters are documentation/mock-tested, not live-account verified. SAM, voice and generated video are unfinished.

## Third-party components

| Components | Evidence | Attribution boundary |
| --- | --- | --- |
| FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic, psycopg | `backend/requirements.txt` | Reused web/data infrastructure, not project-authored frameworks. Python requirements are ranges, not a complete dependency lock. |
| OpenAI Python SDK, httpx, jsonschema, Meta-hosted models/API | Requirements and `backend/app/meta_client.py` | External transport, validation and model services. SentinelX does not author or own the Meta model weights. |
| Pillow, Jinja2, python-multipart, bcrypt, PyJWT | Requirements and integration modules | Reused image, template, upload and security libraries; not original trained models or cryptography. |
| Next.js, React/ReactDOM, TypeScript, Playwright, types, PostCSS, sharp | `frontend/package.json`, `frontend/package-lock.json` | Reused frontend/build/test packages; preserve relevant notices and check licenses. |
| PostgreSQL, Docker/Compose, Caddy, GitHub Actions | Deployment definitions/workflows/docs | Reused infrastructure/services plus SentinelX configuration, not original engines. |
| Google Fonts DM Sans/Plus Jakarta Sans, business media, supplied files | `frontend/app/style.css`, evidence/input records | Third-party/user/generated assets; permissions must be confirmed separately. |

No tracked root project LICENSE/NOTICE was found in this audit. That observation is not a license grant or an opinion on distribution rights. Owner approval and rights verification are required before choosing a project license. This is not a completed legal review of every transitive dependency/asset.

## Submission and demo restrictions to carry forward

From the supplied guide: repository public, maximum four team members, three-minute demo focused on actual new work, Meta model use, and no unauthorized code/data/assets. Simple image analyzers are listed among anti-project examples. Therefore demonstrate the source-to-action workflow and verifiable engineering, while accurately disclosing any foundations; do not position the submission as a generic image analyzer or represent simulated stages as autonomous agents.

The guide's weighted rubric is Impact 30%, Meta tooling 25%, Technical depth/execution 20%, Demo 25%. It lists an indie pool of $400,000 and bonus categories; these guide-derived details are preparation evidence, not a prize promise or confirmation that awards may stack. The accepted Official Rules and organizer clarification still control eligibility.

## Reproducing and completing this record

```powershell
git rev-parse --is-shallow-repository
git rev-list --max-parents=0 --all
git log --all --reverse --format="%H|%aI|%cI|%s"
git show --stat 1075a84
git show 1cb6470 -- .gitignore
git show 9eb567d -- backend/app/mission_routes.py
git show 1a3bc54 -- backend/app/mission_assets.py
```

Compare both dates in the CSV with the explicitly documented boundaries. `git log --before` by itself is not a separate author-date audit. Once organizers confirm the exact allowed interval, repeat the comparison and confirm actual authoring dates with owner records.

Suggested disclosure: “SentinelX uses a pre-kickoff application scaffold and third-party frameworks. Our provenance file identifies that scaffold, recorded event-period feature changes and verified Meta outputs. Only work confirmed as developed in the permitted event window is presented as new work. We seek organizer confirmation of indie-track eligibility for the disclosed foundation.”

Before submission: obtain accepted Official Rules/version or written organizer clarification; confirm the indie scaffold policy and allowed start instant; identify imported/pre-authored source; confirm public access, asset permissions, licenses, team contributors and required AI-assistance disclosure. Maintain eligibility **UNCONFIRMED** until resolved.

**No history deletion, rebase, amend, force push or timestamp alteration was performed for this audit.**


## Explicit pre-kickoff baseline

The 54 recorded pre-kickoff commits are separately listed in [provenance/pre-kickoff-commits.csv](provenance/pre-kickoff-commits.csv). The last such recorded commit is `d0d3c7b4ea4ddb07a21fdb685322cd90d04db38d`, 2026-10-26T16:44:26+05:30 (`docs: guide free-provider development and staging deployment safely`). It contains 38 tracked files. This provides an inspectable foundation baseline, not proof that every later addition was first authored after it.

Its backend source files include:

- `backend/app/agents.py`
- `backend/app/auth.py`
- `backend/app/creative_routes.py`
- `backend/app/inference_routes.py`
- `backend/app/main.py`
- `backend/app/media_routes.py`
- `backend/app/meta_adapters.py`
- `backend/app/model_registry.py`
- `backend/app/orchestrator.py`
- `backend/app/providers.py`
- `backend/app/research.py`
- `backend/app/workflows.py`
- `backend/app/workspace_routes.py`
- `backend/app/workspace_store.py`

Compare baseline and report release with `git diff --stat d0d3c7b4ea4ddb07a21fdb685322cd90d04db38d d25d23b946d60b43b4ae3ac21deb6e13428ebc34`. Review individual diffs before deciding which functions may appear as new work in the submission.
