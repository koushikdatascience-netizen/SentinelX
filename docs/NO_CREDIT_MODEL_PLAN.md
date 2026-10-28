# No-credit model strategy for SentinelX

The project can be developed and demonstrated without claiming the hackathon's $150 hosted Meta API credit. **Credits and a payment-card authorization are separate from the hackathon submission.** Do not claim any hosted Meta inference unless a successful live response has been observed.

## Available modes

| Mode | Backend variables | Meaning |
|---|---|---|
| Safe sample | `INFERENCE_PROVIDER=demo` | Labeled fixtures and deterministic output. Zero paid inference |
| Meta hosted | `INFERENCE_PROVIDER=meta`, `MODEL_API_KEY`, `SENTINELX_MODE=live`, `ALLOW_PAID_INFERENCE=true`, `ENABLE_LIVE_MULTIMODAL=true`, configured per-scope budgets | Real paid requests only after payment verification and explicit spending controls |
| Ollama open-weight | `INFERENCE_PROVIDER=ollama`, `ENABLE_OLLAMA_INFERENCE=true`, `INFERENCE_MODEL=llama3.2:3b`, `OLLAMA_OPENAI_BASE_URL=http://127.0.0.1:11434/v1` | Genuine local inference; no Meta API bill. Only the specific model actually loaded may be claimed |

## Run Ollama safely (on a separate sufficiently provisioned machine)

1. Install a trusted Ollama version from the vendor.
2. Pull an approved open-weight model and verify the actual model and license. Example: `ollama pull llama3.2:3b`. This is **not** Muse Spark or SAM 3.1; do not substitute claims.
3. Verify `ollama list` and `ollama run llama3.2:3b` locally.
4. On a trusted backend host, configure `INFERENCE_PROVIDER=ollama`, `ENABLE_OLLAMA_INFERENCE=true`, and `INFERENCE_MODEL=llama3.2:3b`.
5. The backend endpoint supports only `http://localhost:11434/v1` or `http://ollama:11434/v1`. Keep Ollama private; never publish port 11434 directly.
6. Create an authenticated workspace and run, then POST `/api/v1/inference/test` with `workspace_id`, `run_id`, and `prompt`; verify `provenance=live_ollama`. A configured adapter without a reachable model is not a completed integration.

An Oracle Free VM used for production web hosting may **not** have enough spare RAM/CPU for local LLM inference. Never pull the model on Kamal Woodcraft's shared VM without measuring resources and securing separate limits. Use a separate host if necessary.

## Current limitations

- The open-weight adapter handles **text-only** OpenAI-compatible Ollama chat; it does not enable SAM/video, vision, hosted Meta web search or image generation.
- The main multi-agent business mission currently uses the `MetaClient` contract for live research and structured outputs; Ollama support in `providers.infer()` is not a drop-in replacement for the full mission.
- Budget guard applies to hosted Meta requests; CPU/RAM costs from local inference depend on the host.
- Do not auto-enable live inference on public demo sessions. User-supplied content is untrusted.
- Confirmation of official hackathon model eligibility and all model licenses remains part of the final submission review.
