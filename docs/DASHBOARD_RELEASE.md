# SentinelX dashboard release

## Owner experience

The dashboard is the signed-in home. Nine tool cards open campaign creation, photo review, campaign calendar, creative studio, landing pages, review and export, business strategy, evidence reports and workspace settings. A consistent sidebar keeps frequently used tools available. Hash navigation supports browser back and refresh.

Campaign posts appear as readable cards with captions, calls to action and visual briefs. Copy editing, landing copy editing, deliverable review and customer inquiries open focused dialogs. Escape closes dialogs. Saved generated images and landing previews load from authenticated, workspace-scoped endpoints; opening saved work consumes no model credits.

The dashboard shows stored campaign and page counts, the current campaign and its pending reviews. Labels distinguish Meta AI generated, sample and user-supplied content. Unavailable features do not produce fabricated output. App reservations and connection details are in Settings.

## Review journey

1. Sign in and select a workspace, or create one in Settings.
2. Open Create campaign and enter business facts and a goal. Sample generation is explicitly selected under Generation options; live generation follows the server gates and budget guard.
3. Read the campaign calendar. Edit a post in its dialog, copy its caption or open its visuals.
4. Open Creative studio to retrieve saved images or explicitly generate new concepts.
5. Open Landing pages to preview a saved draft, edit its copy or generate a new page.
6. Open Review & export to record decisions. Publishing an approved self-hosted landing page is a separate explicit action. Social posts are never automatically published.
7. Download the approved pack. Evidence reports remain available for source-backed audit records.

## Verification

Browser coverage exercises account/workspace setup, evidence reports and downloads, the public no-login sample, dashboard navigation, post and page editing, saved visuals across day changes, landing review and publication, approved ZIP export, refresh restoration and mobile overflow. These checks use offline fixtures and make no paid requests. Run `cd frontend && npm run build && npm run test:e2e` with the documented local API configuration in `playwright.config.ts`.

The backend suite and CI also validate owner isolation and approval rules. See [META_API_NOTES.md](META_API_NOTES.md) for capability verification and [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md) for deployment and operational limits. Default repository inference settings remain demo and paid-off; live owner runtime is explicitly configured. SAM and voice remain unsupported. Reservations are not reconciled provider billing.
