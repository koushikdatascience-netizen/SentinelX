# SentinelX operator dashboard — release notes

## Delivered
- Responsive, dark-theme operator dashboard with four views: Overview, New Analysis, Run History, Configuration.
- Email/password sign-up and sign-in; JWT session remains in browser memory (logout clears it; refreshing requires sign-in).
- Business-workspace selector, creation and owner-scoped run history.
- Zero-credit evidence intake: website, goal, title and user-provided excerpt produce auditable proposed research, SEO and creative steps. Input provenance is explicitly **user-supplied, unverified**.
- Offline-safe seven-agent preview (explicitly marked simulated).
- PostgreSQL-backed action proposals and per-action approve/reject decisions. No publishing or external execution occurs.
- Provider configuration and app-local reserved-budget status visible in Configuration.
- GitHub Actions verifies Python backend tests and Next.js build.

## Demo journey
1. Create an account, then a workspace.
2. Select **New analysis** and enter a business goal plus a publicly shareable excerpt.
3. Run **Generate evidence-backed audit** without external API cost.
4. Examine the saved run in **Run history**.
5. Create an action proposal, approve/reject it, and show that execution remains **False**.
6. Return to **Overview** to inspect the persistent activity timeline.

## Production blockers (not part of this completed development milestone)
- Production-ready authentication (registration rate limits, password recovery, stronger abuse protections, account invitations, refresh/revocation).
- Alembic DB migrations and routine database backup/restore testing.
- Robust media storage/processing, real SAM/video inference, verified Muse integration and genuine multi-agent autonomous execution.
- User consent and fully isolated, SSRF-hardened public website retrieval.
- Provider account limits and accurate charge reconciliation. Current limits are app-side conservative reservations, not provider guarantees.
- Production hardening, verified recurring backup operation, GitHub deploy account setup, and an automated Hostinger release. Current Hostinger staging is isolated and audited; see [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md).
- End-to-end browser QA on an actual deployed environment and usability testing.

Keep `INFERENCE_PROVIDER=demo`, `SENTINELX_MODE=demo`, and paid options off until provider Billing is verified. Running as a public internet service without additional hardening is not recommended.
