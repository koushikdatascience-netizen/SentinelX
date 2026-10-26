# Meta integration plan — credit-safe implementation

The Meta Model API credit claim form was announced as coming soon on 26 Oct 2026. Participants are offered $150 subject to the official credit terms; do not assume it is already in the account.

## Model integration boundaries

- Muse Spark: evidence-grounded reasoning, structured research, bounded tool execution.
- Muse Wonder: optional high-depth planning when granted access.
- SAM 3.1: segmentation of consented product / retail imagery; outputs need evidence.
- Muse Image: create optional marketing creatives from approved briefs.
- Muse Voice Transcribe: transcribe consented audio; never default to recording.
- Muse Spark Open: eligible, verified open-weight inference for the bonus award.
- Muse Glimmer: optional small local or partner edge worker.

**Current status:** only a preliminary Spark-compatible text adapter exists, with no verified live test. The workflow preview and model registry are mocks. No other model API integration is implemented yet.

## Credits and billing

1. Obtain official form URL from event organizers.
2. Verify Meta portal credit balance and expiry.
3. Confirm payment card and spending limits.
4. Test each entitled model with one minimal authorized request.
5. Log per-request token and image usage, track budget at app level, stop calls on exhaustion.

## Next engineering increments

- Authenticated organization/project boundaries.
- Durable PostgreSQL action and run storage (not in-memory).
- Secure crawler with DNS pinning and strict egress rules.
- Evidence-linked agent steps and JSON-schema validation.
- Real model adapters, capability detection and integration tests behind flags.
- Approval -> execution -> verification with allowlisted write actions.
- Web dashboard and documented demo.
