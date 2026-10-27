# SentinelX demo readiness — 28 October 2026

## Implemented on draft PR #3 (not merged or deployed)

- Central `MetaClient` for text, image-input analysis and Muse Image, behind explicit flags and prepaid reservations. SDK calls are **mock-tested**, not account-verified. SAM 3.1 and voice fail closed as unsupported.
- Photo upload assessment: true pixel metrics with documented heuristic readiness; Meta rating only after real call. Original uploaded photo is not retained.
- Workspace-scoped 7-day campaign, English/Bengali/Hindi sample fixtures, edit provenance, per-workspace inference attempt quota.
- Bounded creative variants; local sample gradients or opted-in Meta generation; selected variant is only an owner decision.
- Validated landing specs and three autoescaped responsive templates; publication requires recorded approval, consented lead capture and limited inquiry intake.
- Audit trail for approval/reject/reopen, export ZIP with approved-only posts, selected approved creatives, landing HTML and evidence appendix.
- Six-step Next.js Business Studio, interactive guest demo (operator enabled, rate-limited, 20 minute expiry, no paid inference), static `/demo` fallback.
- Public `/api/v1/status` reports live capability only after a recent verified Meta call recorded on the active server; no API key or credits alone count.

## Verification gates

- Only claim passing CI on the **exact head commit** once GitHub Actions concludes successfully. Backend tests, migrations, Chromium journey and Next.js build must all pass.
- Confirm manual text/vision/image capability smoke through GitHub's `meta-live-test` environment, each invocation requiring the operator's explicit approval. Prior 35-token Spark response was nonempty in usage but gave no visible answer; it was **not a verified usable generation**.
- Verify deployed HTTPS host, public demo, page CSP, consent and approval isolation, export correctness.
- Confirm billing consumption in Meta's Usage page after each authorized smoke; reservation caps do not replace provider spend limits.
- Validate owner-supplied campaign example, not scraped customer information.
- Review accessibility and mobile screenshots; inspect browser console and server logs.
- Record the 2-minute script in `docs/DEMO_SCRIPT.md` and complete official submission.

## Remaining blockers and limitations

- PR #2 from Codex is still a draft; PR #3 targets PR #2's branch and therefore **cannot merge directly into main without landing PR #2 first**.
- No real SAM segmentation or Muse Voice capability; no actual Meta service verification for text/vision/image on the final deployed runtime.
- Example creatives are labeled samples; local metrics are not a calibrated marketing score.
- Campaign URL is accepted but **not crawled**; source is owner description only.
- Public guest experience is opt-in and should not be enabled before live rate-limit and data-expiry cleanup is verified; expired records remain in DB until cleanup is added.
- Lead data retention policy, true account-level cost reconciliation, provider quotas, password reset, stronger abuse controls and backups need work.
- No deployment to Oracle, DNS/TLS configuration or real live demo has been performed; existing Kamal Woodcraft website must remain untouched.
- Browser end-to-end test can be considered reliable only when it passes on the PR head.

## Safety defaults

`INFERENCE_PROVIDER=demo`, `SENTINELX_MODE=demo`, `ALLOW_PAID_INFERENCE=false`, `ENABLE_LIVE_MULTIMODAL=false`, `CAMPAIGN_WORKSPACE_MAX_ATTEMPTS=0`, `ENABLE_PUBLIC_DEMO_SESSION=false`.
