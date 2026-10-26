# SentinelX v0.4 — database, authentication, media and dashboard

## Run locally
Create a root `.env` with `POSTGRES_PASSWORD` and `JWT_SECRET` (strong random 32+ character secret). Run `docker compose up --build -d`. API: http://localhost:8000/docs.

For frontend, `cd frontend && npm install && npm run dev`; open http://localhost:3000. By default frontend uses http://localhost:8000. To change, set `NEXT_PUBLIC_API_URL` at build time. CORS accepts localhost:3000 and 127.0.0.1:3000 by default; define `CORS_ORIGINS` for approved deployments.

## Implemented
- SQLAlchemy User, Workspace and WorkflowRun tables on PostgreSQL via DATABASE_URL; automatic `create_all` development initialization. Schema migrations (Alembic) pending.
- Register/login with bcrypt password hashes and signed, expiring JWT bearer tokens.
- Workspace CRUD basics and mock workflow runs scoped by owner.
- Image file validation/metadata extraction (PNG/JPEG/WEBP, 5MB/20MP bounds) with no inference.
- Optional Muse Voice transcription and Muse Image generation with real HTTP/client calls when `SENTINELX_MODE=live` and `MODEL_API_KEY` is configured. **These provider calls have not been integration-tested with a real account.**
- Dashboard uses browser-memory token (no persistent login). No uploads in frontend yet.
- Existing legacy prototype endpoints remain unsecured; this repo is NOT ready for public exposure.

## Required hardening before public deployment
Remove/protect legacy unauthenticated actions and research, add JWT refresh/revocation, login rate limiting, CSRF/replay considerations, tenant membership roles, Alembic, persisted action approvals and audit trails, egress-safe crawler, upload antivirus and server-side durable media storage, quota enforcement, content moderation, automated live-provider integration tests, observability, and production TLS. Treat `MAX_LIVE_REQUESTS_PER_SESSION` as a weak in-memory guard only, NOT a spend limit.

The new workspace run endpoint stores a **mock** orchestrator preview; it does not yet perform research, segmentation, or real execution. Approved actions are not executed automatically.

## Tests
`cd backend && python -m pytest -q`. GitHub Actions runs backend pytest on push. No paid API calls are made by tests.

## Docs
- Meta Voice endpoint: https://dev.meta.ai/docs/speech-to-text
- Muse Image: https://dev.meta.ai/docs/overview
- SAM: https://dev.meta.ai/docs/sam/overview
