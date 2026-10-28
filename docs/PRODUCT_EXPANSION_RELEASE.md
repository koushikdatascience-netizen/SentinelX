# Business research and private-data expansion

Implementation status dated 28 October 2026. This is an incremental Phase A release on the existing application, not completion of the entire expansion brief. Exact deployed SHA and production verification belong in the release handoff. Tests alone do not establish live provider availability.

## Existing code and architecture decisions

The baseline `d444a3e34c6f70203186e89c711954ca6ffcdbec` had real Meta text/vision/image/search/voice evidence, one-page missions, reusable textual media interpretations, campaigns, editable landing drafts, approval decisions, separately authorized publication and public verification. It lacked recursive website discovery, relational facts, private dataset ingestion and a unified research report. Existing authentication, workspace ownership, DNS-pinned HTTPS, SQLAlchemy, budget guards and CI/CD are reused.

Three additive tables provide relational integrity: `research_jobs` (workspace, status, checkpoint, lease, timestamps), `business_facts` (workspace, unique fact key, typed value, source evidence, visibility, verification), and `business_datasets` (workspace, filename/version, hash, size, original bytes, deterministic analysis). Facts retain source URL/ID, hash, extraction method/time, verification time and owner review events. A changed source invalidates prior confirmation. A linked social profile is only a candidate until owner review; owner confirmation is not platform verification.

The existing PostgreSQL database acts as the bounded job queue. The current deployment runs one application process with one research worker. Claims use a conditional database update, each attempted request is persisted before transport, page checkpoints retain progress, and a seven-minute expired lease becomes paused. Recovery requires explicit resume, not an automatic retry. Cancellation is checked between requests; an in-flight request may finish. Queue state survives process restarts. This is not a distributed crawler with cross-worker per-host scheduling; horizontal scaling needs that work first.

## Implemented modules and APIs

| Module | Working behavior |
| --- | --- |
| `site_research.py` | Same-host HTTPS traversal, navigation and sitemap discovery (one index child), robots rules, sequential rate-limited retrieval, deterministic HTML/JSON-LD extraction, social-link candidates, page audit findings |
| `research_jobs.py` | Durable queued/running/completed/failed/paused/cancelled jobs, pre-request accounting, ownership-preserving relational fact upserts, bounded worker recovery |
| `intelligence_routes.py` | Research creation/history/control, identity confirmation, fact review, saved search candidates, report JSON/printable HTML, deterministic evidence lookup, public-only context handoff |
| `data_parser.py` / `data_hub.py` | Actual CSV/XLSX/PDF/TXT/JSON parsing, multi-file batches, version history, deduplication, preview, type/missing/duplicate checks, numeric totals with explicit units, original/safe CSV download and deletion |
| `ResearchWorkspace.tsx` | Overview, Twin, Website, Social, Competitors, Data Hub, Report, Ask evidence and truthful integration availability in one responsive workspace |

Routes require owner/workspace authorization:

- `POST/GET /api/v1/intelligence/research`; `GET /research/{id}`; `POST /research/{id}/control/cancel|resume`.
- `GET /twin`; `POST /identity`; `POST /facts/{id}/review`.
- `GET /competitor-candidates`, `/integrations`, `/report/{id}?format=json|html`; `POST /ask`.
- `POST /research/{id}/prepare-context`: only collected public evidence, never private datasets.
- `POST/GET /api/v1/data-hub`; `GET /{id}`, `GET /{id}/download?format=original|safe_csv`, `DELETE /{id}`.
- Existing `POST /api/v1/missions` accepts `research_job_id`: validates ownership, website and completed state, reuses snapshots with original capture times and bounded prompt excerpts, then uses the existing explicit live flags and budget/attempt guards. Samples cannot replace these sources.

## Limits and security

Research is owner-only, with one active job and eight starts per workspace per day, forty retained jobs, at most twelve pages and depth two, forty requests, a five-minute processing window and a seven-minute lease. Each response is capped at 1 MB. HTTPS port 443 only; every DNS answer must be public, connections pin the checked numeric address and validate original-host TLS, redirects stay on the authorized host, proxy environment variables and cookies are not used. Robots failures block that host, disallowed pages are not fetched, and no JavaScript, authentication bypass or CAPTCHA bypass occurs. Queries are excluded to bound navigation. Incomplete coverage and failures remain visible. Performance, mobile layout, complete accessibility and conversion scores are not fabricated from metadata.

Static parsing extracts titles, descriptions, headings, canonical/robots metadata, HTML inquiry signals, media inventory and selected JSON-LD claims. It does not interpret all imagery or video. Public source claims remain distinct from independently verified business truth. Competitors are owner-selected or chosen from existing source-linked search candidates. No competitor sales or advertising performance is inferred.

Private uploads require an owner account and consent. Limits: five files/6 MB per batch, 2 MB per file, twenty versions/20 MB per workspace, 2,000 rows/40 columns, one sheet per workbook and twenty PDF pages. Expanded ZIP sizes/ratios are inspected before loading XLSX; macros and external workbook links are rejected. Untrusted file parsing runs in a separate process without model credentials, with a 20-second wall timeout and Linux 512 MB/12-second CPU limits. Two parser slots bound local concurrency. Windows tests retain wall/size limits but cannot apply Unix resource limits. This is process/resource isolation, not a hardened container sandbox against a parser zero-day.

Spreadsheet formulas are never evaluated, and safe CSV export prefixes formula-like cells. PDF extraction runs no scripts, external links or OCR. Scanned PDFs fail clearly. Text decoding accepts UTF-8 or BOM-marked UTF-16; CSV detects comma, semicolon, tab or pipe delimiters. Date recognition is restricted to unambiguous ISO values. Numeric totals preserve units; mixed currencies are not added. Numeric identifiers can still require owner interpretation. There is no automatic cross-file join, currency exchange conversion or sales trend inference.

Original private bytes remain in authenticated PostgreSQL records and backups, not public files or model context. Deletion removes active original/analysis records and redacts saved local answers referencing the dataset. Access-controlled operator backups follow the existing retention policy. This release does not claim application-level encryption of private dataset blobs. The printable report contains private schema/quality metadata, so the owner should review it before sharing. No private upload is sent to Meta by these new routes.

`Ask evidence` is deterministic retrieval plus computed dataset summaries, with sources and saved tool traces. It cannot execute instructions embedded in web pages/files and does not invoke a model or external action. It is not yet the universal reasoning/tool-execution agent from Phase B. Existing publishing approval and separate authorization controls remain unchanged.

## Migration, backup and rollback

Migration `0012` creates only the three new tables/indexes/constraints. No existing columns or records are removed. Before preparation, the existing SentinelX backup command produced and restore-tested `/srv/sentinelx/backups/sentinelx-20261028T073301702709589.dump`. Fresh migration and upgrade-from-0011 tests use disposable databases and verify existing owners/workspaces remain. CI also migrates and tests PostgreSQL with automatic schema creation disabled. The existing deployment script creates another restore-tested backup before release.

Rollback: restore the previous application containers using the existing release mechanism and leave additive tables at revision 0012. The older app does not depend on them. Do not downgrade or restore over production as a routine rollback. A schema downgrade deletes new research/data and requires a separate reviewed recovery decision. No deploy scripts, reverse proxy, unrelated business infrastructure or inference defaults are changed.

## Acceptance status before production verification

| Requested capability | Status and boundary |
| --- | --- |
| Login/workspaces, campaigns, Meta creatives, approvals, publication, verification | Existing live-verified features; full regression required for this release |
| Multi-page discovery and durable jobs | IMPLEMENTED BUT NOT INTEGRATION-VERIFIED until a real post-deploy crawl completes |
| Twin/source facts and social review | Implemented; website links and owner confirmation only, no social posts/private statistics |
| Maps/reputation provider | NOT IMPLEMENTED; explicitly unsupported, no provider data claimed |
| Competitor comparison | Implemented for owner-selected retrieved pages; saved search candidates may be irrelevant |
| Multiple business-file uploads | Real parsers and local calculations implemented; use labeled synthetic files for production verification |
| Evidence report and exports | JSON and printable HTML implemented; no binary PDF/PPTX claim |
| Universal Agent | Only local evidence lookup implemented; general planning and external tools remain incomplete |
| Opportunity-to-action | Connected to existing guarded mission pipeline; final Meta request cap is exhausted, so no new paid live proof is implied |
| Google OAuth, CRM, MCP, website chatbot | NOT IMPLEMENTED in this release; product adapters/credential lifecycle still required |
| Dataset relationship joins, monitoring, broader creative formats | NOT IMPLEMENTED; no decorative success states |

## Validation and judge walkthrough

Offline browser fixtures replace only the public transport; auth, durable jobs, parsing, data calculations, review, reports and navigation use real application routes. Screenshots exercise desktop/mobile report layout. Backend tests cover robots/sitemaps/SSRF transport scope, metadata extraction, unsafe files, deterministic values, ownership, idempotency, cancellation/recovery, source refresh and guarded snapshot handoff. Existing campaign, approval, landing and Meta HTTP-contract suites must stay green. Final counts and actual deployment evidence are recorded separately after those runs finish.

Walkthrough: sign in → choose workspace → Research & data → confirm website/name → consent and start research → inspect actual pages and limitations → review a social candidate if discovered → select relevant competitors → upload labeled business exports → preview schema/totals → ask evidence → export report → prepare improvement → explicitly run guarded Meta planning when quota permits → edit and approve → separately authorize publication → inspect the existing public verification receipt. A missing source, unsupported provider or exhausted quota remains visible instead of producing an invented result.

## Follow-on visual research, public social search and short-form campaign guidance

The research interface now inventories same-site HTML images and brand signals such as `og:image`, icons, alt text and image paths. The owner can request deterministic pixel measurements (dimensions, aspect ratio, dominant colors and technical image metrics) without a model call. The filename, metadata and layout only make an asset a **probable** logo/brand image; they do not verify it as the official logo. For a deeper image interpretation, the owner selects an inventoried same-host image and explicitly consents to one budgeted Muse Spark visual request. It uses the existing Meta budget guard and retains the image hash, source asset URL, local color measurements and model provenance. Cross-host CDN images are not eligible for this first version; videos and iframes are not inspected by the HTML crawler.

Social account links remain owner-reviewable candidates. A separate owner-initiated one-request search can look for publicly indexed posts linked to a selected profile and saves source citations. This does not connect to Instagram/Facebook APIs, guarantee the search index is complete, access private posts/analytics, count engagement or verify account ownership. Search results can be absent or stale. The public-web search uses Meta's existing Responses [`web_search` tool](https://dev.meta.ai/docs/protocols/responses) through `MetaClient`; no Tavily or SerpAPI key is configured, and no search-engine HTML scraping is used. The image interpretation path follows Meta's [image-understanding documentation](https://dev.meta.ai/docs/image-understanding); the still-image generator follows its [image-generation API](https://dev.meta.ai/docs/image-generation). This release has no verified video-rendering endpoint.

Market search now asks for **up to 15 plausible nearby competitors** and never calls them a ranked top 15 without support. Search may return fewer; owners select relevant business sites before collection. A research run accepts up to 15 competitor URLs and checks one static homepage from each, with bounded robots and request limits. The comparison report reports observed HTML differences and sourced homepages, then frames suggested changes as hypotheses. It has no distance verification, Maps/review data, competitor social analytics, pricing extraction or sales/advertising data.

Each newly generated seven-day campaign item includes caption, hashtags, CTA, an image-generation prompt, and a 10–60 second vertical-video shooting plan with hook, timed scenes, on-screen copy, optional voiceover and ending. Owners can edit the image prompt and use it in the existing Muse Image generation flow. The video artifact is production guidance for filming real owner-approved footage; it is not a generated/rendered video. Existing campaign exports include this guidance. Older saved campaign records may not contain the new fields. Existing review, approval and explicit publication controls continue to apply.

These paths were verified with local route/HTTP mocks and sample-mode fixtures. This change did not spend a live Meta request. A live visual/social search on the owner's account is still pending because its recorded workspace allowance is exhausted; no Tavily/Serp credential or private social account connection was added.

Parser references: [Python robots parsing](https://docs.python.org/3/library/urllib.robotparser.html), [CSV parsing](https://docs.python.org/3/library/csv.html), [openpyxl read-only mode](https://openpyxl.readthedocs.io/en/stable/optimized.html), [pypdf text extraction and memory caveats](https://pypdf.readthedocs.io/en/stable/user/extract-text.html). These document parser behavior, not live SentinelX verification.
