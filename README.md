# SentinelX — Meta AI Developer Hackathon 2026

Evidence-first, human-supervised business intelligence dashboard. Development software; deployment and hosted Meta inference remain unverified.

## Implemented

- FastAPI API and Next.js dashboard with email/password authentication.
- Owner-scoped workspaces, persisted runs and review decisions (SQLite locally, PostgreSQL in staging).
- Audits from owner-supplied **unverified** excerpts, with no crawling or model calls.
- Explicit seven-agent simulation, media validation/demo intake and model readiness views.
- One-time action approval decisions; no external execution. Owner-only Markdown audit export.
- Optional provider inference with conservative app budget reservations, not reconciled charges or provider billing caps.

## Local development (PowerShell)

Use Python 3.11+ and Node.js 22. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
$env:JWT_SECRET = (.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:INFERENCE_PROVIDER = "demo"
$env:ALLOW_PAID_INFERENCE = "false"
$env:ENABLE_LIVE_MULTIMODAL = "false"
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm ci
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
npm run dev
```

Open http://127.0.0.1:3000, register, create a workspace and generate an audit with a self-authored sample excerpt. Refreshing requires signing in again. SQLite data is stored in the backend working directory.

Local signup is open. Shared staging sets `ALLOW_PUBLIC_REGISTRATION=false` and uses `REGISTRATION_ALLOWED_EMAILS` (comma-separated approved test emails). An empty list closes signup; existing accounts can still sign in. This gate does not verify email ownership or provide complete abuse prevention.

## Verification

```powershell
cd backend
..\.venv\Scripts\python -m pytest -q
cd ../frontend
npm ci
npm run build
```

GitHub Actions runs backend tests and a production frontend build. See [readiness](docs/DEMO_READINESS.md), [dashboard release](docs/DASHBOARD_RELEASE.md), [manual Meta smoke setup](docs/META_GITHUB_ONLY_SETUP.md), and [isolated Oracle staging](deploy/ORACLE_STAGING.md).

## Safety and remaining work

Keep demo mode, paid inference disabled, live multimodal disabled and legacy routes disabled in staging. Legacy crawler routes require DNS pinning and network egress safeguards before untrusted public access. Never commit secrets or customer data.

Meta's $150 promotional credits were visible in the owner's Billing interface on October 27, 2026. Requests, permissions and exact schemas remain unverified. The manual smoke workflow is gated and single-call.

Remaining work includes auth abuse controls, migrations and tested backups, workspace quotas and provider reconciliation, consented real media inference, source verification, browser E2E QA, isolated TLS staging and a recorded demo. See [engineering status](docs/ENGINEERING_STATUS.md). Existing Kamal Woodcraft production infrastructure is unrelated and must be preserved.
