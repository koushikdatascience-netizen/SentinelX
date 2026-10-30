# Social research failure handling

A completed platform attempt means its public search returned evidence. It does
not mean the final structured report passed validation or that a full social
feed was retrieved. Failed runs now expose saved source excerpts and the stage
that stopped: synthesis or citation/mapping validation.

Fixed public-safe errors distinguish incomplete provider output, structural
validation, platform mapping and citation/account mismatches. Provider payloads,
keys and invalid model text are never exposed. The generic historical error
cannot establish the exact cause of an already completed production failure.

The final prompt explicitly supplies eligible owner source IDs, separates
candidate accounts and asks for compact platform reports within the existing
output limit. Citation and exact platform mapping validation remain mandatory.

On an explicit new request from a failed social run, the service reuses completed
searches only when the saved social signature (selected URLs, owner context and
business profile) is unchanged, all selected searches completed, evidence exists,
and current owner consent/live gates pass. Only report synthesis is called again,
using a new persisted run and the unchanged budget guard. Duplicate request IDs
never repeat calls. Changed inputs or incomplete searches use normal research.
There is no automatic paid retry or sample report fallback.

No schema migration, paid-default change or budget increase is included. Offline
tests exercise provider failures, invalid output, persistence, request reuse,
consent, workspace isolation and changed-input behavior. They do not diagnose or
verify the owner's prior live response.
