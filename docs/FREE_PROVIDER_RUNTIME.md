# No-credit inference options (operator-controlled)

SentinelX does not require activating Meta Model API billing to develop and demonstrate the core research, evidence, mission and approval workflows. Claims that a model ran must be supported by actual call provenance.

## Default: no external inference

Keep these settings in the private deployment environment:

```dotenv
INFERENCE_PROVIDER=demo
ALLOW_PAID_INFERENCE=false
SENTINELX_MODE=demo
ENABLE_LIVE_MULTIMODAL=false
META_APP_BUDGET_CENTS=0
ENABLE_OPENROUTER_FREE=false
ENABLE_OLLAMA_INFERENCE=false
```

This is the recommended configuration until the actual Meta account is authorized.

## Option A: OpenRouter free model

Only after obtaining your own key, choosing a currently available model **whose exact ID ends with `:free`**, and agreeing to the provider's privacy and quota policies:

```dotenv
INFERENCE_PROVIDER=openrouter
INFERENCE_MODEL=your-chosen-model:free
OPENROUTER_API_KEY=enter-in-private-host-env-only
ENABLE_OPENROUTER_FREE=true
ALLOW_PAID_INFERENCE=false
```

Restart the backend container after changing the private env file. A paid model is rejected even if a different feature enables paid inference. The adapter makes a single scoped request, does not automatically retry or fall back to a paid model, and records `provenance=live_free_provider` only when a valid completion returns. Free-model quota, routing, service availability and provider privacy are not guaranteed. Never commit the key; never expose it in a browser env variable. The current dashboard exposes safe, non-inference workflows by default, so an operator must deliberately use the authenticated inference endpoint or opt-in run flow.

## Option B: Ollama on a trusted private host

```dotenv
INFERENCE_PROVIDER=ollama
INFERENCE_MODEL=your-installed-local-model
OLLAMA_OPENAI_BASE_URL=http://ollama:11434/v1
ENABLE_OLLAMA_INFERENCE=true
ALLOW_PAID_INFERENCE=false
```

The existing Ollama adapter restricts the endpoint to localhost or Docker's `ollama` service hostname. There is **no Ollama service bundled in the Hostinger Compose file**: provision it on a trusted internal network, verify reachable model and memory requirements, and connect it only when capacity permits. Do not run a large open-weight model on the small web-server allocation or expose Ollama publicly.

## When Meta access becomes available

The Meta SDK adapter exists, but access to credits, authorized account payment, true models and successful calls must be verified separately. Do not set `ALLOW_PAID_INFERENCE=true` until the operator approves the cost exposure, per-workspace limits and provider Billing. The `/api/v1/status` endpoint reports recent successful requests rather than confusing configuration with working integrations.

## Validation

1. Run all backend tests and Next.js build in GitHub Actions.
2. Test demo flows and approval queue without external costs.
3. Enable exactly one model route in staging and make one authorized bounded test using owned workspace and run IDs.
4. Confirm provider provenance and latency; disable the route if rate limited.
5. Record a demo which distinguishes measured live output from fixtures and simulations.

**No OpenRouter model execution, Meta credit activation or production inference success is claimed by this document.**
