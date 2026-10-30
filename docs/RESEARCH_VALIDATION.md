# Keyword and competitor research audit

Both Workbench tools use Muse Spark 1.3 via Meta Responses API web_search.
The shared client requires a completed response and exactly one completed search
call, bounded summary, and valid public HTTPS source annotations or provider
result links. Source links do not independently prove the business claims.
Provider-result-only summaries are explicitly labeled as lacking span citations.

Each request uses the owned persisted run, existing app/workspace/run reservation,
timeout and zero SDK retries. Saved results and exports require workspace
ownership; request IDs reuse completed results and block replay of failed or
pending requests. No fixture substitution or separate campaign-quota claim occurs.

Audit corrections:
- Keyword instructions now request keyword clusters, search intent, long-tail
  phrases and hashtag proposals rather than three competitor candidates.
- Full owner requests are retained in valid bounded JSON alongside the saved
  business context, offering/location inputs and UTC research date. Earlier code
  cut requests after 650 characters and could cut serialized business context.
- Search budget rejection remains a safe ValueError and reaches the route as
  HTTP 429 rather than a generic provider failure.

Current limits remain: one bounded search call, low search context and up to
three source-linked competitor candidates in the concise answer. This is not an
exhaustive top-15 competitor investigation, independently measured keyword
volume/difficulty, live social analytics or verified trend detection. Trend
claims require dated source evidence; otherwise suggestions are hypotheses.
The UI displays a saved prose report and source links, not a validated keyword
spreadsheet or a structured competitor comparison matrix.

Tests use mocked HTTP to check search tools, result/citation validation, gates,
budget rejection and research-specific instructions. Route tests cover request
retention, saved business context, idempotency, quota separation and isolation.
No new paid inference or live-account outcome verification is included.
