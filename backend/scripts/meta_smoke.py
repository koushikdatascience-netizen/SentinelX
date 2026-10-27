"""Single paid Meta Model API smoke test. Never prints API credentials."""
import os
import sys
from openai import OpenAI

def main():
    key = os.getenv("MODEL_API_KEY")
    if not key:
        print("ERROR: MODEL_API_KEY not configured", file=sys.stderr)
        return 2
    if os.getenv("META_SMOKE_ACK") != "I_ACKNOWLEDGE_ONE_PAID_REQUEST":
        print("ERROR: Set META_SMOKE_ACK to explicitly authorize one real request", file=sys.stderr)
        return 2
    model = os.getenv("META_MODEL", "muse-spark-1.3")
    try:
        result = OpenAI(api_key=key, base_url="https://api.meta.ai/v1", timeout=30, max_retries=0).chat.completions.create(
            model=model,
            messages=[{"role":"user","content":"Reply with exactly: OK"}],
            reasoning_effort="minimal",
            max_completion_tokens=128,
        )
        print("Provider: Meta Model API")
        print("Model:", model)
        choice = result.choices[0] if result.choices else None
        text = (choice.message.content or "").strip() if choice else ""
        reason = getattr(choice, "finish_reason", None)
        # Whitelist metadata rather than logging raw responses or hidden reasoning.
        print("Finish reason:", reason if reason in {"stop", "length", "content_filter", "tool_calls", "function_call"} else "unknown")
        print("Visible text present:", bool(text))
        usage = getattr(result, "usage", None)
        if usage:
            print("Prompt tokens:", getattr(usage, "prompt_tokens", "unknown"))
            print("Completion tokens:", getattr(usage, "completion_tokens", "unknown"))
            details = getattr(usage, "completion_tokens_details", None)
            print("Reasoning tokens:", getattr(details, "reasoning_tokens", "unknown"))
        if not text or reason != "stop":
            print("Smoke test incomplete: no complete visible answer; no retry made.", file=sys.stderr)
            return 1
        # Fixed-prompt probe: log only whether it matched, never arbitrary output.
        print("Expected OK received:", text == "OK")
        if text != "OK":
            return 1
        print("Smoke test succeeded; check Meta Billing/Usage for actual charges.")
        return 0
    except Exception as error:
        # Do not dump request objects, headers or full provider responses.
        print("Smoke test failed:", type(error).__name__, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
