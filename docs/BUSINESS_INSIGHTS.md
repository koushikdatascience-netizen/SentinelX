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

### Expanded market research and image improvement (local implementation)

Expanded research is an explicit, default-off option. It adds one separate
competitor search and one keyword/content search to the existing business/social
identity search. Each uses the central client with a single bounded web-search
tool call, no automatic retry and the same app/workspace/run caps. A full run uses
at most five provider requests (three searches, text report, selected visual
contact sheet); no quota or spending ceiling is increased. This is bounded public
web research, not an exhaustive deep-web survey or a top-15 ranking.

The text report now receives labeled provider search excerpts as well as page,
owner and document evidence. Returned result snippets and provider-written URL
annotation spans retain distinct provenance; neither is independently retrieved
page evidence. Up to three competitor comparisons must cite a matching search
URL/quote and a separate matching quote from the owner's details or collected
pages. Up to six keyword opportunities carry intent and suggested use. Unsupported
ideas are marked hypotheses; no volume, trend, distance or sales metric is added.

The Insights view includes market/keywords and social-coverage sections. Expanded
searches and their failures are also visible in Sources. Supplied social links
remain pointers: restricted social platforms are not directly scraped. Publicly
indexed text may support qualified findings; image/post visual quality needs an
accessible saved or uploaded image.

Brand assets offers an image review modal with explicit consent to send that
image to Meta. It verifies owner scope and actual bytes against the saved hash,
then saves one structured visual review with strengths, concrete improvements,
post guidance and an editable regeneration prompt. Reopening results is free of
inference. Preparing the generation brief performs no request; submitting it
makes one new image concept and links the saved review/source image. The original
pixels are not sent to the image generator, so this is not a pixel-preserving
edit. The original image is retained.

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

## Recoverable visual design reports

Saved-evidence text generation never implicitly analyzes screenshots. The Visual
design section offers a separate explicit request using saved business logo and
selected desktop/mobile screenshots. It creates a persisted research/model run,
charges the existing budget guard once before vision transport, and never repeats
business search or page collection. Structured findings include the panel, visual
area, observation, proposed change, rationale, priority, acceptance check and an
editable design brief. Original hashes are checked against actual bytes and each
numbered panel maps exactly once to its result.

Owners can additionally choose one source-backed competitor candidate already in
that report. This explicitly captures only that candidate page, desktop and phone,
using the existing robots-aware DNS-pinned collector; restricted platforms are
rejected. Up to two business and two candidate panels are compared in the same
single vision request. Search-only candidate findings never become visual
comparisons without actual captured images. Candidate identity/proximity remains
unconfirmed. A failed capture or analysis stops clearly; no automatic retry.

The source text report remains intact. Repeated request IDs and completed linked
requests reuse saved output; explicit retries after failure create new runs under
the existing rate and spending caps. Consent withdrawal stops queued visual work.
Visual output is a separate readable section with authenticated source previews,
panel filters, rationales, verification checks, source links and Markdown export.
Preparing a concept retains the owned report and source asset linkage; submitting
the editable brief creates an original visual concept, not an edit of the source
website or its pixels. Scaled overviews cannot establish fine text readability or
interaction behavior; loading shells are inspection gaps. Text analysis is
instructed not to mistake excerpt gaps for missing sections or distinct call and
WhatsApp channels for an established contact inconsistency.

## Platform-specific social intelligence

Social insights is a dedicated section, including for businesses without a website
or a prior crawl. An explicit request selects up to three saved social URLs per
batch. Each profile gets one separate bounded public search for the exact profile,
indexed content and comparable accounts; one shared structured synthesis follows
only if usable evidence exists. The maximum is selected-profile count plus one
Meta request, under the same atomic spending caps. Existing source text and visual
reports remain saved separately. Older batches stay in research history and the
social section presents the latest saved report for each available profile.

Owner-profile findings require matching quotes from indexed URLs belonging to that
exact profile or its post paths. Candidate examples require separate exact search
URLs and quotes. Reports cannot omit or duplicate selected platform mappings. If
profile evidence is unavailable, coverage is explicitly insufficient; content
experiments can still use supplied business facts. Experiments include format,
topic, hook, CTA and a measurement plan, and can prepare an editable platform post
without making a generation request. Actual post images are reviewed separately.

Restricted feeds are not directly scraped. Full-feed completeness, growth rates,
sales attribution and reasons for decline are not established by snippets.
Goals/performance notes are optional, owner-supplied and unverified. All failed
requests remain failed; worker replay never automatically repeats paid requests.

## Campaign quota correction

The legacy campaign counter was shared with research, documents/media and creative
operations. Workbench tools now rely on their atomic Meta spending guard rather
than consuming that unrelated attempt allowance. Actual campaigns use a separate
`cq:` counter in the existing scoped counter table, bootstrapped from saved live
campaigns. The configured campaign maximum and all Meta app/workspace/run spending
ceilings remain unchanged. Historical shared counts and uncertain cost
reservations are preserved. Campaign quota and spending-cap failures are explained
as application controls, not as exhaustion of the owner's Meta credit balance.
