# Business onboarding and research

Owners without a completed business profile enter setup immediately after signup or login. Existing users are asked to complete setup once per workspace. Signup signs the owner in after successful account creation. Returning owners with a completed profile enter their workspace normally.

The profile stores business name, industry (including Other), description, optional website, platform-specific social links, address/service area, business email and phone. Logo, image and document uploads are optional. PNG, JPEG, WebP, PDF, DOCX, XLSX, TXT and CSV are accepted within file and workspace storage limits; executable, macro and encrypted files are rejected. Uploaded text extraction is bounded and does not imply independent verification.

Saving never starts research. The next step offers Start research or Skip for now. Skipping completes onboarding without queuing collection or model calls. Starting requires recorded consent. Business & research provides editable owner details and separate Sources, Website pages, Brand assets, Insights and Activity tabs. Collected evidence and prior research inputs remain immutable snapshots when an owner edits their profile.

## Collection and costs

- Durable database jobs run sequentially in a background worker and checkpoint progress after each page. Reloading the browser does not restart the job. A lost running job is marked interrupted after its lease expires; uncertain paid requests are not replayed automatically.
- Up to ten linked, same-domain, public HTTPS HTML pages per collection run. Query URLs, login/cart/account URLs and binary downloads are excluded. Relevant product/service/about/contact paths are prioritized. Remaining discovered URLs can be collected explicitly in another run; this does not claim a complete internet-wide crawl or guarantee every page is discoverable.
- Every resource uses validated public DNS and a direct pinned TLS connection. Redirect destinations are checked before retrieval. Robots rules are checked per origin; unavailable rules fail closed except a missing robots file (404). No login, cookies, captcha bypass, private-network retrieval or automatic network retry.
- Chromium renders stored HTML with website JavaScript, embeds, video and service workers disabled. The browser is offline; requests are fulfilled through the pinned fetcher. Desktop (1440 wide) and mobile (390 wide) screenshots retain full rendered height up to 16,000 pixels, with clipping disclosed. Dynamic websites can be incomplete; a screenshot is a static rendering, not proof of a fully functional site.
- Up to two useful raster logo/image assets per page are saved. The full bounded HTML image inventory remains visible. Asset SHA-256 is calculated from actual bytes; a supplied hash must match. All originals and previews require owner/workspace authentication.
- One AI search, one cited text report and one numbered visual contact-sheet review at most per research run, when owner selected and operator enabled. All calls use MetaClient, campaign attempt limits and app/workspace/run budget reservations. Default paid flags remain off. No model call is needed for collection, screenshots, uploads, manual edits or viewing stored reports.
- Vision receives up to four selected logo/desktop/mobile panels, with explicit per-panel findings and a separate summary. Stored source hashes and normalized input hashes remain separate. No visual findings are invented when the model fails.
- Search results remain candidate pointers, not independently retrieved source claims. Social-only businesses retain supplied profile and uploaded materials plus permitted search evidence; the application does not fabricate missing online details.

## Access policies and hackathon eligibility

Public availability alone does not grant permission to automate collection, store copyrighted assets or ignore platform terms. Owner consent is necessary but does not replace platform permission. Direct collection from Facebook, Instagram, YouTube, LinkedIn, TikTok, X and Google Business/Maps surfaces is blocked in this implementation. Their URLs can be saved and appear in permitted provider search results. Approved platform APIs are not connected by this change; owners can upload material they are authorized to use.

Official references reviewed October 29, 2026:

- [Meta: How We Combat Scraping](https://about.fb.com/news/2021/04/how-we-combat-scraping/): automated collection without Meta permission violates its terms.
- [YouTube Terms of Service](https://www.youtube.com/t/terms): restrict automated access, subject to stated exceptions.
- [Meta hackathon public event page](https://dev.meta.ai/events/global-hackathon): selected participants must accept separate Official Rules; public information is not an individual eligibility determination.
- [Playwright network documentation](https://playwright.dev/python/docs/network): browser request routing and service-worker restrictions used for isolated rendering.

The participant guide supplied by the owner says projects violating legal, ethical or platform policies, or using code, data or assets without rights, are disqualified. It also lists generic or policy-sensitive anti-project examples: medical advice, basic RAG, simple image analyzers, simple education chatbots, job screening, nutrition/personality/sports analyzers and political/war projects. This business workflow must be demonstrated as the connected business research and supervised action product, with accurate disclosure of event-period contributions. Eligibility remains subject to the accepted Official Rules and organizer interpretation; this implementation does not establish or guarantee approval.

## Verification

Backend tests cover owner isolation, persistence, explicit start/skip semantics, consent withdrawal, request idempotency, real byte hashing, rejected uploads, robots restrictions, private-address rejection, lost-worker recovery and failed model calls. Browser regression covers onboarding, editing, social links, logo upload, reload and explicitly starting research. The Docker CI check renders real desktop/mobile screenshots from authored fixtures with container networking disabled. These tests do not consume Meta credits or prove a new live-account AI result.
