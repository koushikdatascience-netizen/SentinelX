# SentinelX agent instructions

SentinelX is an evidence-first, human-supervised business intelligence project for the 2026 Meta AI Developer Hackathon.

## Start here
- Read `README.md`, `docs/DEMO_READINESS.md`, `docs/DASHBOARD_RELEASE.md`, `docs/META_GITHUB_ONLY_SETUP.md`, `docs/HOSTINGER_DEPLOYMENT.md`.
- Backend: Python FastAPI in `backend/app`; run `cd backend && python -m pytest -q`.
- Frontend: Next.js in `frontend`; run `cd frontend && npm install && npm run build`.
- DB: SQLAlchemy; staging PostgreSQL. Owner/workspace isolation is essential.

## Critical guardrails
- Never expose or commit MODEL_API_KEY, any secrets, or customer data.
- Meta's $150 promotional credits were visible in the owner's Billing interface on October 27, 2026; real API requests and permissions are **not** yet verified.
- Default `INFERENCE_PROVIDER=demo`, `ALLOW_PAID_INFERENCE=false`, `ENABLE_LIVE_MULTIMODAL=false` in public/staging. Do not change defaults casually.
- Meta smoke action must remain manual, gated, single-call, and secret-safe. Review provider's exact supported schema before treating adapter as operational.
- Action approvals are decisions, not executions; never claim external publishing or autonomous business impact.
- User-supplied website content is marked unverified; do not state that a website was crawled or independently fact-checked.
- Legacy global-memory routes are disabled by default; do not turn them on in public staging.
- Existing Kamal Woodcraft production site is unrelated infrastructure. Do not modify its Nginx, DB, DNS or containers without resource review and backups.

## Next engineering tasks
1. Verify API compatibility using manual Meta smoke workflow and sanitized logs, then adapt client carefully.
2. Add production-safe request cost accounting for all Meta endpoints, provider usage reconciliation and workspace-level quota.
3. Implement actual source-backed agent workflows and media processing with consent and evaluation tests.
4. Add SSRF-safe crawler only with pinned DNS/egress safeguards; keep unauthenticated crawling disabled.
5. Run browser E2E tests, verify isolated TLS staging on Hostinger, prepare an accurate 2-minute recorded demo.
6. Before hackathon submission, explicitly separate simulated outputs, actual Meta inference, and verified outcomes.

Only report success with test output or deployed evidence.
