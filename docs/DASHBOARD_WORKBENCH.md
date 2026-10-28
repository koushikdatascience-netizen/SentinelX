# Dashboard workbench

The business consent declaration is a single responsive checkbox with a separate wrapping text span. The optional AI preference is labeled as a generation choice; unavailable AI appears as an explanatory status instead of a nonresponsive checkbox. Desktop/mobile browser checks exercise the checkbox and text bounds.

The dashboard shows the actual latest research state, page count and screenshot count. View live progress opens a modal with an animated agent indicator, saved stages, activity timestamps and collection limitations. Data refreshes every four seconds. Counts and completion marks come from stored job evidence; the UI does not invent a percentage or mark unavailable AI work completed.

## Tool flows

Dashboard cards open focused modals, while saved campaign, landing and review workflows remain accessible through navigation.

| Tool | Input | Stored output / limits |
|---|---|---|
| Campaign | Saved business brief, goal, language and platforms | Existing strategy and seven-day campaign workflow; creation opens in a modal and successful output opens the saved calendar |
| Competitor research | Optional saved business context, prompt, industry, location | One budgeted cited Meta web search; candidate businesses require identity/relevance review. No fabricated rating, rank, proximity or exhaustive coverage |
| Post generator | Context, prompt, platform, optional industry/location | Validated post, caption, hashtags, image-generation prompt, reel/shorts scene guidance, CTA and disclosed assumptions. No publishing |
| SEO keywords & hashtags | Context, target market, prompt | One cited Meta web search for keyword/intent/hashtag ideas. No invented search volume, trend score, popularity rank or difficulty statistic |
| Image generator | Prompt, optional saved business context, aspect ratio | One Muse Image call; private stored image with model/provenance and download |
| Image editor | Owner image, dimensions, contain/crop, rotation, format | Local Pillow processing, no inference. PNG/JPEG/WebP, 8 MB input, 64–2400 output pixels per dimension |
| Document parser & converter | PDF/TXT/CSV/Markdown, page/chunk range, explicit processing consent | Local extraction, up to 20 MB, 25 pages/chunks per request, up to 20k characters per page/chunk, Markdown/TXT/JSON export. Physical PDFs over 2000 pages rejected; scanned pages flagged for OCR. This is not OCR or LlamaParse-equivalent layout reconstruction |

Tool requests are authenticated and scoped to an owned workspace. Requests persist their ID, input signature, status, provider/model and result in existing workflow storage; no database migration is required. Repeated successful requests with the same ID reuse the result. Changed input under the same ID conflicts. Pending/failed requests never replay a paid call automatically. All Meta calls use MetaClient, existing campaign attempt controls and app/workspace/run reservation caps. Existing paid defaults remain off. New tools do not substitute sample output when live configuration is unavailable.

Document results persist extracted output and source digest, not the original large file. The owner must keep/reselect the file to extract later batches. Image originals/outputs require authenticated downloads. Only the approved campaign delivery-pack flow claims approval; standalone tool exports are drafts requiring review.

No new live provider requests are needed for regression checks. Mocked provider tests establish contracts and request behavior, not new live-account verification. See BONUS_AWARD_READINESS.md for eligible-model and submission requirements; adding tool cards or a model selector does not establish prize eligibility.
