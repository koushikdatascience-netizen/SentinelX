# SentinelX verified product state — 28 October 2026

The core owner workflow now uses real Meta inference. PR #10 was merged and release `a23217066465b06b2f6d96504fdbf17e9f6759ff` deployed through Hostinger run [40595722228](https://github.com/koushikdatascience-netizen/SentinelX/actions/runs/40595722228).

## Real runtime evidence

One credit-conscious run in the owner's existing workspace created:

- Campaign `0539ada8-b38e-4b9a-b352-5e247e53d120`: real Muse Spark audit and seven distinct daily posts, provenance `live_meta`.
- Creative `8f6a6a21-6db6-47f8-9478-f1d4ea4dd659`: real Muse Image output, 1600 × 1600 WebP, with a separate Muse Spark image-input assessment. Model brief match was 96/100; this is a subjective assessment, not measured business impact.
- Landing draft `e35ab857-c318-41fa-b8f7-588703fec0a9`: real Muse Spark copy, selected generated hero image, authenticated HTML preview returned 200. It remains unpublished for owner review.

Exactly four provider requests were used: campaign, image generation, image assessment, landing copy. The shared database recorded $0.20 of conservative reservations. Actual provider billing was not independently reconciled.

A deployed Chrome check opened the existing owner session and verified the real audit, generated image, landing preview and saved campaign restoration after reload. It made no paid calls. Public capability status recorded successful text, vision and image requests. Main CI [40595388852](https://github.com/koushikdatascience-netizen/SentinelX/actions/runs/40595388852) reported 135 tests passing on SQLite, 135 on PostgreSQL, 4 browser journeys passing, both Docker builds and the frontend production build.

## Owner experience

Sign in with the owner account to open the dashboard. Its tool cards open dedicated campaign, photo, strategy, visual, landing and review views. The Live AI enabled status reflects the configured runtime; each saved output separately identifies its provenance. The saved campaign selector loads stored work; changing days restores the corresponding saved visuals. Approval cards identify actual copy and pages. Approval is a recorded decision; publishing a self-hosted landing page is a separate action. Approved-only export is a real ZIP.

Guest workspaces and the explicit sample checkbox use labeled fixtures and cannot call paid models. Requested live generation fails clearly instead of silently substituting a sample.

## Operational limits and remaining scope

The owner explicitly activated live inference. Unconfigured installations still default to demo with paid calls off. Initial cumulative reservation ceilings are $2 per app/workspace and $0.50 per run, with 20 generation attempts per workspace. These are application controls, not a provider-enforced billing limit.

SAM masks and voice transcription remain unsupported and must not be presented as implemented. Website URLs are not crawled by the Studio. Source evidence is owner supplied and unverified. Social account publishing and measured ROI are not implemented. Broader production account recovery, abuse controls and provider billing reconciliation remain separate engineering work.
