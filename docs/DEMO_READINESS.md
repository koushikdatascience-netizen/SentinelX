# SentinelX hackathon demo readiness — 27 October 2026

## Working offline-safe demo path
1. Start PostgreSQL + FastAPI + Next.js with separate SentinelX staging Compose; no Kamal Woodcraft production changes.
2. Register as a test user, sign in and create a business workspace.
3. Choose New Analysis, enter a URL and a self-authored or consented business excerpt (do not use sensitive customer data).
4. Generate an audit. Inspect attributed **owner-supplied unverified evidence** and proposed SEO, research and creative workstreams.
5. Save approval decisions in Run History. They are deliberately recorded-only and have no external side effect.
6. Download the audit report (Markdown) with the same user-scoped access checks.
7. In Configuration, upload a sample product image for validation and a sample recording for demo-mode voice intake. Image dimensions are real local parsing; speech transcription is **not run** in demo mode.
8. Show seven Meta-model integration readiness states. No hosted Meta model execution has yet been verified.

## Additional systems still required for full hackathon ambitions
- Deploy and health-check the staging stack with domain, HTTPS and safe registration gate.
- Real provider calls with verified billing and *specific* API schemas for Meta models.
- Hosted or partner-verified Muse Spark Open / Glimmer inference for the $10k open-weight prize.
- SAM video or image segmentation, actual multimodal interpretation, media storage and consent.
- Agent planning/research that verifies sources and measures output quality; approvals that trigger narrowly authorized operations with recorded artifacts.
- Strong controls: production account authentication, distributed rate limits, durable metrics, Alembic migrations, egress-safe crawling, key rotation, actual-cost reconciliation, backup/restore.
- Live browser end-to-end tests and a recorded demo video.

## Safety
Meta's $150 promotional credits were visible in the owner's Billing interface on October 27, 2026. Actual API requests and permissions remain unverified. Keep `SENTINELX_MODE=demo`, `INFERENCE_PROVIDER=demo`, `ALLOW_PAID_INFERENCE=false`, `ENABLE_LIVE_MULTIMODAL=false`, `ENABLE_LEGACY_ENDPOINTS=false`. The `/api/v1/meta/readiness` endpoint does not make API calls. Do not advertise unavailable models as running.

## GitHub CI
Backend Python tests plus Next.js production build run automatically. Final live deployment requires access to the target Oracle VM and DNS provider; no such deployment has been executed.
