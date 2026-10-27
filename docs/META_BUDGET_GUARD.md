# Meta API credit preservation (27 October 2026)

## Claim and verification
The accepted participant submitted Cerebral Valley's $150 credit form. Email does **not** verify credit activation. Manually check Meta Billing for the promotional credit and expiration. Never paste API keys or card details into chat or git.

## Official pricing
- Muse Spark 1.3: input $1.25 / 1M tokens, output $4.25 / 1M tokens, cached input $0.15 / 1M.
- Muse Wonder: input $4 / 1M tokens, output $20 / 1M.
- Muse Image: $0.01 / generated image.
- SAM 3.1: $2.50 / 1k images; $0.20 / 1k video frames.
- Grounded web search: $2.50 / 1k queries.
- Muse Voice: billed per audio hour; consult the complete current pricing table.
Source: https://dev.meta.ai/docs/pricing-rate-limits

Published limits are per team, not per API key. See your team's Limits page for authoritative account limits.

## Safety settings
- `INFERENCE_PROVIDER=demo`: no paid model inference.
- `ALLOW_PAID_INFERENCE=false` (default): Meta text provider disabled; OpenRouter limited to `:free` models.
- `META_APP_BUDGET_CENTS=500` (default): a **$5 app-local reservation allowance**, not an account limit. PostgreSQL persists reservations; inference fails closed when allowance exhausted. Reservations deliberately do not auto-refund on API errors.
- `OTHER_APP_BUDGET_CENTS=100`: default $1 local allowance for other providers.
- `ENABLE_LEGACY_META_ANALYZE` and `ENABLE_LIVE_MULTIMODAL` default to disabled. Legacy and multimodal live calls are currently **not covered by the reservation guard**. Do not turn these on in deployment without dedicated accounting protections.
- `GET /api/v1/inference/budget`: authenticated app allowance and reserved amount; **not actual Meta balance**.
- Existing rate limits from Meta are not spending controls. Meta's Spend Limit is an **alert only**, not a hard cap: https://dev.meta.ai/help/billing/spend-limit-alert

## Recommendation
Keep `INFERENCE_PROVIDER=demo` or a selected free provider for regular tests. After credits appear, test a *single* short Muse Spark response, inspect provider's Usage and Billing pages, and turn off paid inference when finished. Never assume promotional credits stop paid overages.

Not production ready: authentication on old routes, per-user API quotas, durable actual-usage reconciliation, provider retries, media processing limits, public internet exposure, multi-tenant audit, and tracing remain separate tasks.
