# SentinelX — Meta AI Developer Hackathon 2026

**Autonomous Multimodal Business Intelligence & Action Engine** — initial v0.3 backend scaffold.

## What works today

- FastAPI health endpoint: `GET /health`
- `POST /api/v1/analyze`: explicitly labeled demo assessment, or optional Meta Model API preliminary assessment (no website crawl)
- `POST /api/v1/research`: one public homepage snapshot with source-linked, proposed-only agent actions
- `POST /api/v1/actions`: create proposed actions
- `GET /api/v1/actions/{id}`: inspect proposed action
- `POST /api/v1/actions/{id}/review`: approve or reject once; **no execution occurs**
- Docker Compose localhost binding, pytest tests, GitHub Actions CI

## Local quickstart (Windows PowerShell)

```powershell
git clone https://github.com/koushikdatascience-netizen/SentinelX.git
cd SentinelX/backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SENTINELX_MODE = "demo"
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and test with:

```json
{"website":"https://example.com","goal":"Increase local qualified customer leads"}
```

Run tests from `backend`:

```powershell
python -m pytest -q
```

## Optional model API mode

Set `SENTINELX_MODE=live` and `MODEL_API_KEY` locally. Never commit API keys. The configured in-process request guard is **not** a billing cap and resets on restart. Check account access, model availability and current API docs before enabling paid calls.

## Security and implementation status

**Development-only, not production-ready.** The crawler rejects obviously unsafe hosts, private IP answers, redirects, nonstandard ports, and oversized HTML, but suffers potential DNS-rebinding / time-of-check-to-time-of-use risks; it requires DNS pinning and network egress controls before untrusted public exposure. Review endpoints lack authentication, tenancy and durable storage. Proposals are never automatically executed. Do not expose this API publicly without hardening.

Planned work: authenticated tenants and PostgreSQL persistence; safe crawler; orchestrated agents with evidence provenance; SAM vision, Muse Image and Voice adapters; approved execution and verification; Next.js command center; real credentials and billing guardrails. Model integrations beyond the preliminary text adapter are **not implemented yet**.

## Deployment

Local development only; nothing has been deployed. GitHub Actions checks source quality automatically.
