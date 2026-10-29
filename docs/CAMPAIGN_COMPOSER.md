# Campaign requirements and direct dictation

Campaign creation uses the saved owner/workspace business profile. Owners choose
a goal (or custom goal), duration (7, 10 or 30 days), tone, language and platforms,
then provide campaign-specific requirements. The form no longer asks them to
re-enter business name, website or the offer. Existing API callers may still send
an explicit business description; that input remains unverified owner content.

The calendar has one content row per day and shows the actual requested duration.
Seven days uses up to one Meta request; ten days up to two; thirty days up to five.
Each batch has at most seven days, with exact day/platform assignments, structured
validation, no SDK retries and the same app/workspace/run budget guard before
each call. The campaign attempt allowance is claimed once for the whole campaign.
No spending caps or inference defaults are changed.

Validated batches are persisted in the owned model run. Failure retains the valid
prefix and reports its run ID, without creating a falsely complete campaign or
retrying paid calls. Request IDs reuse completed campaigns and reject replay of
pending/failed requests. Requirements and tone are saved with campaign metadata;
older seven-day campaigns remain readable.

The mic sits beside the requirements submit button. Clicking it is the explicit
recording action and requests native browser microphone permission; no separate
checkbox is needed. The adjacent disclosure explains that stopping sends audio to
Meta, inserts editable text and does not submit the campaign. Other prompt fields
use the same direct mic control.

Recording is bounded below 60 seconds, downmixed/resampled locally to 24 kHz mono
PCM16 WAV, and sent once with a recording request ID. Audio/transcripts are not
persisted. Tracks stop on completion or exit; late permission responses are
discarded after unmount. Permission denial preserves typed text and sends no
audio. Generation is disabled while dictation is active. Spending-cap errors are
reported separately from microphone failures; no sample transcript is inserted.

Offline validation covers duration/batch mapping, input persistence, duplicate
campaign and recording IDs, saved partial output, permission denial, synthetic
browser recording/WAV upload and editable transcript insertion. These checks mock
provider HTTP and do not establish a fresh live-account transcription result.
