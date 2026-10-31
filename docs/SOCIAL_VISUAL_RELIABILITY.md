# Social and visual report reliability fixes

Social research uses a dedicated social search purpose rather than generic competitor instructions. Exact owner-profile hits are prioritized before the existing bounded evidence selection. Candidate evidence must belong to the selected platform; unrelated directories remain saved as search evidence but do not trigger paid synthesis by themselves. This does not provide authorized full-feed access or guarantee an account is indexed.

An explicitly requested retry with unchanged owned inputs reuses completed platform searches and requests only failed platform searches plus synthesis. It does not run automatically. Request IDs, owner consent and existing app/workspace/run spending caps remain enforced. Quotes and account mappings remain strict: invalid claims are rejected rather than relabeled as verified.

Visual review verifies original image hashes, then deduplicates identical normalized image bytes before contact-sheet construction. Original evidence remains retained. Panel numbers and schema bounds reflect the actual unique images sent; missing/duplicate/out-of-range findings still fail validation. A candidate identical to the owner's normalized preview stops before vision inference. Known visual failures have fixed, safe messages rather than leaking model payloads.

The Visual design UI distinguishes a report never requested from a failed request and from a running visual request. An unrelated running social job is not labeled visual analysis. An unavailable report is not itself evidence of a failed Meta call. Users explicitly choose visual review and consent; merely opening the tab makes no paid request.

Offline verification uses mocked HTTP and fixture images. These changes do not establish the live server's failure cause without its exact error, do not bypass social access restrictions and do not make a new live account compatibility claim.
