# Development without Meta credits

## Available providers
- **Demo**: no external call, no key, no charges.
- **OpenRouter**: choose an actual available `:free` model in your account. Public free plan is limited (currently 50 requests/day). API key must be stored server-side, never in frontend or GitHub.
- **Groq**: available free developer tier, but models/rate limits and eligibility vary by account. Explicitly choose a model from the current Groq console. Requests are real and account limits may change.
- **Meta**: future hackathon credits. Real inference requires `ALLOW_PAID_INFERENCE=true` plus valid account credits and key.

## Configuration for Docker Compose (root .env)

```ini
POSTGRES_PASSWORD=replace_with_strong_password
JWT_SECRET=replace_with_random_secret_at_least_32_chars
INFERENCE_PROVIDER=openrouter
INFERENCE_MODEL=replace-with-current-free-model-id:free
OPENROUTER_API_KEY=replace-locally-never-commit
ALLOW_PAID_INFERENCE=false
```

To test Groq instead set `INFERENCE_PROVIDER=groq`, `GROQ_API_KEY`, and a valid `INFERENCE_MODEL` from its console. No default Groq model ID is pinned because availability changes.

```bash
docker compose up --build -d
docker compose logs --tail=100 api
```

Start frontend separately: `cd frontend && npm install && npm run dev`. Register and log in; create a workspace; select **Use configured inference provider** when starting a new run. API status: `GET /api/v1/inference/status` (requires bearer token). Server saves the output in the PostgreSQL workflow run record. Input website URL is **not crawled** by this route.

**No real provider calls have been authenticated against user's accounts yet.** API keys and billing state must be configured by the account holder. A `:free` suffix is enforced in OpenRouter mode by default; a model’s actual availability/quota is ultimately controlled by the provider. The max call setting is **not** a robust enforceable billing quota. Keep infrastructure private and impose network and billing limits before public deployment.

## Deployment boundary
Docker Compose supports local/staging execution. No public server credentials, domain, TLS setup, or CI deployment secrets have been provided; do not label the project publicly deployed. Legacy unauthenticated prototype routes and missing migrations/rate-limits are blockers for internet-facing production.
