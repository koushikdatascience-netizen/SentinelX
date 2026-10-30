# Document parsing with Meta multimodal PDF input

The owner-scoped parser extracts existing PDF text layers and UTF-8/UTF-16 TXT,
CSV and Markdown locally. Scanned pages can be transcribed by Muse Spark via
`MetaClient.review_media`. No Tesseract, PDFium or external OCR service is used.

The form selects Meta reading by default but requires a separate explicit
checkbox consenting to send scanned pages to Meta and save the AI output.
Processing still requires authenticated ownership and the local-storage consent.
The API accepts `use_meta` and `meta_consent`; defaults are false for existing
clients. Live provider/key/paid/multimodal gates remain mandatory and unchanged.

Meta mode limits the requested PDF batch to five pages. Only pages lacking a
text layer are copied into a new in-memory PDF, capped at 5 MB. One Responses API
request transcribes that subset, under the existing app/workspace/run budget
reservation, timeout and zero SDK retries. Files are sent inline with store=false;
no persistent provider Files resource is created. Original page numbers are
specified and validated exactly once each, including unreadable pages. Invalid,
missing, duplicated or inconsistent results fail rather than being misassigned.
Scanned-page results carry live_meta provenance; local text remains user_supplied.
Names, numbers and tables must be checked against the source document.

The original upload is limited to 20 MB. The upstream upload limit may be lower;
the example Nginx limit is 11m. Non-JSON errors and 413 upload rejections are shown
clearly. No infrastructure configuration or spending cap is changed.

Request IDs reuse completed results and block pending/failed paid requests from
being replayed. Local extraction is saved before Meta inference and retained on
failure. Opening or exporting results never requests inference. Larger documents
require explicit next-page submissions. No automatic paid retry or sample
transcription is substituted. Word files and guaranteed layout reconstruction
are unsupported.

Contract references: [Meta file handling](https://dev.meta.ai/docs/file-handling)
and [Responses API](https://dev.meta.ai/docs/protocols/responses). HTTP-mocked
integration checks do not establish live-account PDF success. A fresh paid test
has not been run.
