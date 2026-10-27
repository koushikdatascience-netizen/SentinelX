# Meta Model API setup without a development PC

## 1. Add your key as a GitHub Actions environment secret
Repository: https://github.com/koushikdatascience-netizen/SentinelX

Settings → Environments → New environment → name **meta-live-test**. Add a required reviewer if available to prevent accidental paid calls. Inside this environment choose **Environment secrets** → **Add secret**:
- Name: `MODEL_API_KEY`
- Value: your full private Meta Model API key

**Do not** add the key to a repository file, Codespaces terminal transcript, issue, screenshot or this chat. The Actions job does not echo the key.

## 2. Run a single live smoke test
Actions → **Meta API single-call smoke test** → **Run workflow** on main.
After publishing the updated workflow/script, enter exactly `I_ACKNOWLEDGE_ONE_PAID_REQUEST` and approve the environment if required. This triggers **one actual paid API call** with at most 128 combined reasoning/visible output tokens, minimal reasoning effort, 30-second timeout and no automatic retries. The fixed prompt asks only for `OK`. Logs contain whitelisted finish metadata, token counts and whether the expected text was received; raw responses and hidden reasoning are not logged. Empty, truncated or unexpected text fails the smoke check. If it fails, do not repeatedly rerun it; inspect the safe metadata first.

Check Meta's Usage and Billing screens afterward. GitHub Actions is ephemeral; this test does not deploy the application or enable live traffic.

## 3. Live application configuration later
On the private deployment server (not on GitHub), configure `MODEL_API_KEY`, `INFERENCE_PROVIDER=meta`, `META_MODEL=muse-spark-1.3`, `ALLOW_PAID_INFERENCE=true`. Keep `META_APP_BUDGET_CENTS=100` for preliminary tests and `ENABLE_LIVE_MULTIMODAL=false`. The reserved-budget cap is **not** a Meta billing hard stop.

The Hostinger staging Compose locks the app in demo mode and does not receive the Meta key. Do not enable a live key on public staging without deliberate budget controls and owner authorization. The deployment architecture is documented in [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md).

## 4. Codex pickup
Clone the repo and read `docs/DASHBOARD_RELEASE.md`, `docs/DEMO_READINESS.md`, `docs/HOSTINGER_DEPLOYMENT.md` and this file. Run backend tests and Next.js production build. Inspect GitHub Actions checks before deployment. Never enable public anonymous paid inference.

If `muse-spark-1.3` does not work with the declared chat completions API, check your Meta account's Models documentation and correct the exact model/endpoint under a tested change rather than guessing.

## October 27 verification and credit conservation

The [first smoke run](https://github.com/koushikdatascience-netizen/SentinelX/actions/runs/40545827402) completed the request and reported 21 prompt / 35 completion tokens, but returned empty text. That proves a successful API response, not a usable generated answer. The owner subsequently reported $149.99 promotional credits remaining and ₹0.00 payable; precise per-request charges were not reconciled.

Meta's [reasoning documentation](https://dev.meta.ai/docs/reasoning) confirms that hidden reasoning consumes the output-token limit and is billed as output, and supports `reasoning_effort="minimal"`. This makes reasoning exhaustion a plausible explanation for the empty 35-token response; the original log omitted finish reason and reasoning-token count, so the cause is not proven.

The [Chat Completions schema](https://dev.meta.ai/docs/protocols/chat-completions) documents `max_completion_tokens` and the `choices[0].message.content` response shape. The app now requests minimal Meta reasoning, rejects empty or incomplete answers without retry, and returns token counts on success. Conservative app reservations are retained on failure because tokens may already have been consumed.

Regression checks use mocked responses and spend no credits. No further live request is required to run those checks. Keep demo defaults until one deliberate follow-up produces a complete visible answer; do not rerun the old script expecting its 35-token behavior to change.


## Central client update (October 28)

The manual workflow now selects exactly one capability per dispatch: text, vision or image. It uses MetaClient and ephemeral scoped accounting. Both ALLOW_PAID_INFERENCE and ENABLE_LIVE_MULTIMODAL must be true even for text, along with INFERENCE_PROVIDER=meta. Scope caps default to zero in the application; see [META_API_NOTES.md](META_API_NOTES.md) for ownership, required per-workspace/run budgets and unsupported SAM/voice boundaries. The workflow supplies tightly scoped test flags only for its own job. No live call was made to validate this refactor.
