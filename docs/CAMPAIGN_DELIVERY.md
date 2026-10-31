# Campaign history, visual batches and final delivery

Campaign history shows creation time and a short ID so campaigns with the same
goal remain distinguishable. The active campaign ID is restored per workspace;
older records remain on the server. History supports explicit pagination.

The visual editor starts with the selected post's image prompt. The owner can
edit it before generation; the actual prompt and real image bytes are saved with
the variant. Manual generation uses request IDs to prevent paid replay and no
longer consumes the unrelated campaign counter. Live image output is read using
the verified b64_json contract. Images are saved before optional visual scoring,
so a scoring failure does not discard a paid image.

Generate all missing visuals is explicit authorization for one image per missing
post and selection of draft choices for review. Existing variants are reused.
A persisted batch calls one step at a time with deterministic child request IDs;
all Meta reservations use the same parent run budget in addition to workspace/app
caps. Optional AI scoring is skipped in this flow. A budget/provider failure
stops the batch and preserves saved progress. Larger campaigns may stop at the
configured run cap; no cap is raised or evaded. Interrupted running steps are
not automatically replayed. Saved pending batches can be continued explicitly.

Final review requires exactly one selected visual per post and explicit owner
confirmation of the complete campaign. It records approval events for posts and
selected visuals, rejects previously rejected items until explicitly reopened,
and saves a timestamped snapshot with actual-byte image hashes. This is not
social publishing. Current content, selected images and approval state are
checked again on export; changed/reopened campaigns require a new final review.

Final JSON preserves the exact approved content, source/provenance labels,
reviewer/time and image references. CSV and Excel have separate columns for
captions, hashtags, CTA, image guidance/prompt, scripts, image paths and hashes.
CSV formula-leading text is prefixed with an apostrophe; Excel strings remain
literal strings. ZIP includes JSON, CSV, Excel and the approved selected images.
API image URLs require workspace authentication; bundled image paths work in the
ZIP. Sample campaigns and sample visuals stay labeled as samples.

No schema migration, infrastructure change or paid-default change is included.
Tests use fixture images or mocked provider HTTP; no new live-account generation
or business outcome is established by the offline checks.
