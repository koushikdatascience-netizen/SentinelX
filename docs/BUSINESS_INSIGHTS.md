# Business research → useful improvements

The first product milestone is a persistent report that lets an owner decide what
to improve and inspect why. The original five-capability product vision remains
in ORIGINAL_PRODUCT_SCOPE.md. This milestone does not certify that entire vision
as production complete.

## Report contract

- Every accepted text finding cites a saved source and a matching normalized quote.
- Reports contain at least one supported finding; empty model output is rejected.
- New reports request a summary, website area, suggested priority, specific change,
  rationale and verification check. Older saved reports remain readable without
  invented priorities or acceptance criteria.
- The report separates improvements, strengths and unknowns. Evidence expands on
  demand; its source link remains available. Exporting or reopening saved results
  performs no inference.
- Text inputs contain bounded excerpts from the beginning, middle and end of up
  to four selected website pages, plus owner details and up to two document
  excerpts. The serialized prompt stays below the MetaClient input bound.
  Excerpts are incomplete evidence; an omitted feature cannot be called absent.
- Text cannot establish colors, layout or image quality. The existing numbered
  contact-sheet review uses actual saved logo/screenshots and retains individual
  panel mappings. Its absence is explicitly visible in the report.

## Requests and failure recovery

Research is independent of the campaign attempt quota. Its existing enqueue rate
limit, consent checks, owner isolation, operator gates and atomic Meta app,
workspace and run reservations still apply. No budget was increased.

A failed text report may be requested again explicitly from saved evidence. Each
new request uses a new persisted run; repeating a request ID or requesting while
its linked run is queued/running returns the existing run. Failed requests are
never replayed automatically. An explicit retry does not repeat collection,
search or screenshot review. Uncertain provider failures retain reservations.

## Verification and remaining boundary

Backend tests cover source bounds, quote validation, structured recommendations,
exhausted budgets, campaign-quota independence through mocked HTTP, persistence
and explicit retry idempotency. The browser journey covers report sections,
evidence links, export contents, reload and mobile overflow. All use offline
fixtures or mocked provider transport; they do not establish live output quality.

Page redesign and visual generation still use the existing draft tools. This
report does not alter or publish the source website. Connecting selected findings
to editable drafts and verifying explicitly approved delivery is the subsequent
part of the original product loop. It must retain the source recommendation and
require review of the exact draft before any authorized publication.
