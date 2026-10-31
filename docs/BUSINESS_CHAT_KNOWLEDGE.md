# Business chat, knowledge and local data

The dashboard is a chat-only canvas, without business-summary cards or saved-deliverable grids. The plus button selects up to three explicit tools; selection makes no paid call. Sending runs the selected tools and then prepares one answer. With no tools selected, general questions use one chat call and no search or generation tools. Saved business context is used only when relevant. Strategy, marketing, finance, data and design are advisory perspectives combined in one answer, not independently executing agents. External publishing is never performed by chat.

## Voice prompts

Existing prompt microphones sit inside their textareas. Clicking asks for browser microphone permission directly. Stopping sends bounded audio through the existing authenticated, consented, budgeted Meta transcription route. The result appends to the latest editable field text, including edits made while recording. Dictation never submits the business question or campaign. There is no microphone consent checkbox; the button and field explain the transfer. File-storage and scanned-document consent remain separate.

## Business knowledge

Business & research → Knowledge base accepts PDF, DOCX, TXT, Markdown, CSV and XLSX, with explicit storage consent and saved business-material consent. Limits: 8 MB per file, five files per selection, existing 80 MB workspace storage cap. Original bytes and SHA-256 are retained privately under the workspace owner. Local extraction and spreadsheet profiling make no model requests.

Research, campaign generation and chat retrieve bounded, relevance-ranked saved excerpts. Private documents are not inserted into public search queries. Retrieval adds context to an existing synthesis request rather than making an embedding or per-document inference request. Claims in owner documents remain user supplied and unverified.

Local PDF extraction covers the first 20 pages. For image-only pages, the owner can explicitly request up to five selected pages per Meta reading action. Existing PDF/model guards, live flags and run/workspace/application spending caps apply. Saved page transcriptions are reused; failed request IDs never automatically replay paid work. PDF reading has the existing adapter's stricter payload bounds. It is not unlimited whole-document analysis.

## Data and visualizations

CSV and XLSX profiling and calculations run locally: sums, averages, min/max, row counts, distinct counts, bounded filters, grouping and ISO date month/year groups. Up to 20,000 rows and 60 columns are analyzed; truncation and ignored nonnumeric values are disclosed. XLSX defaults to the first worksheet, uses saved cached formula values and does not recalculate formulas. Numeric-looking identifiers require owner judgment. No code, SQL, macros, external links or shell commands execute.

Chat can ask Meta for one validated calculation plan against the selected saved dataset. The server computes it locally and renders the real values as a chart and table. The same response must not invent results before calculation; a follow-up can use the saved calculation. The knowledge tab also provides calculation controls needing no AI request at all.

## Requests and evidence

Chat requires authentication, owned workspace, saved business profile, and saved material consent when knowledge/data context is enabled. Images require explicit attachment consent and a hash check. All live calls use MetaClient and its existing budget guard; defaults remain demo and paid-off. No sample answer substitutes for an unavailable live service. Completed chat requests and conversations persist and can be reopened; pending or failed paid requests are not automatically replayed. Citation quotes are matched to the actual context sent. Quote matching does not independently establish business facts or measured outcomes.

Verification uses mocked model HTTP and synthetic microphone audio. It does not establish new live account compatibility or real-world business impact.

## Explicit tool selection in chat

Available selections: web search, image generation, a 7-day Instagram/Facebook campaign, post generation, competitor research and keyword research. Selections clear after a successful message so a follow-up does not accidentally repeat paid tools. Sending with selected chips is explicit authorization for their bounded paid actions plus one answer. Each Meta call, including campaign batches, uses the same parent chat run budget as well as workspace/application caps. No cap is raised. Campaign attempt allowances still apply. An image request is limited to 1,000 characters and generates one original concept rather than editing an attached photograph or filling all campaign rows.

Completed outputs persist after each step and are shown inline. Campaigns open the existing editable campaign sheet; generated images are private workspace assets. If a later tool or final answer fails, completed results survive. The failed request ID cannot replay paid work. An explicitly prepared new request is a new paid operation. The same message guides each selected tool; output does not silently become a new generation prompt. Search results are public evidence pointers, not independent verification.

Documents, local image editing, landing pages and review/export retain their dedicated workflows through Open full tools. They require their existing inputs and approvals. Selecting advisory focus areas affects one answer and does not invoke separate agents. Dataset calculations remain the existing local allowlisted engine. Nothing in chat publishes externally.

Typing supports Enter to send and Shift+Enter for a new line. The in-field mic inserts editable text without submitting. Conversation changes are disabled during recording/transcription and pending requests. Context and optional adviser perspectives are collapsed behind Context; default chat does not include the private knowledge base unless enabled. File/image transfer and tool consent remain explicit.
