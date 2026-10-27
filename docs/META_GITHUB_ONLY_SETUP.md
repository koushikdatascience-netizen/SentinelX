# Meta Model API setup without a development PC

## 1. Add your key as a GitHub Actions environment secret
Repository: https://github.com/koushikdatascience-netizen/SentinelX

Settings → Environments → New environment → name **meta-live-test**. Add a required reviewer if available to prevent accidental paid calls. Inside this environment choose **Environment secrets** → **Add secret**:
- Name: `MODEL_API_KEY`
- Value: your full private Meta Model API key

**Do not** add the key to a repository file, Codespaces terminal transcript, issue, screenshot or this chat. The Actions job does not echo the key.

## 2. Run a single live smoke test
Actions → **Meta API single-call smoke test** → **Run workflow** on main.
Enter exactly `I_ACKNOWLEDGE_ONE_PAID_REQUEST` and approve the environment if required. This triggers **one actual paid API call** with at most 35 output tokens, 30-second timeout and no automatic retries. Wait for the job result and inspect the sanitized response. If it fails, retrieve the exception type only; do not paste your token or raw HTTP headers.

Check Meta's Usage and Billing screens afterward. GitHub Actions is ephemeral; this test does not deploy the application or enable live traffic.

## 3. Live application configuration later
On the private deployment server (not on GitHub), configure `MODEL_API_KEY`, `INFERENCE_PROVIDER=meta`, `META_MODEL=muse-spark-1.3`, `ALLOW_PAID_INFERENCE=true`. Keep `META_APP_BUDGET_CENTS=100` for preliminary tests and `ENABLE_LIVE_MULTIMODAL=false`. The reserved-budget cap is **not** a Meta billing hard stop.

The proposed Oracle staging Compose deliberately locks the app in demo mode. Do not put a paid key into it until the host is secure and hardening is complete. Server installation and DNS access have not been verified.

## 4. Codex pickup
Clone the repo and read `docs/DASHBOARD_RELEASE.md`, `docs/DEMO_READINESS.md`, `deploy/ORACLE_STAGING.md` and this file. Run backend tests and Next.js production build. Inspect GitHub Actions checks before deployment. Never enable public anonymous paid inference.

If `muse-spark-1.3` does not work with the declared chat completions API, check your Meta account's Models documentation and correct the exact model/endpoint under a tested change rather than guessing.
