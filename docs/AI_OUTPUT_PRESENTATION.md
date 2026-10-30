# AI output presentation

Saved model text is rendered using a shared React Markdown component with GFM
support for headings, emphasis, lists, quotes and tables. The stored payload,
source citations, provenance, approvals and export content remain unchanged.
Rendering makes no model calls and adds no business performance claims.

Research results use a report header, readable body and source cards. Post drafts
separate captions, hashtag chips, visual briefs, numbered video scenes and calls
to action. Business, visual and social insights use the same typography and
labeled recommendation blocks. Campaign sheets retain their editable columns.
Document pages retain literal transcription text with improved spacing rather
than applying Markdown semantics to the uploaded document's content.

Raw HTML is not executed. Generated links allow only HTTP/HTTPS or fragment
references; remote images in Markdown are represented as text, avoiding automatic
image fetches. Actual saved business images still use authenticated asset routes.
Tables scroll within their container on small screens, source links have clear
focus styles, and reduced-motion settings are respected.

Dependencies: [react-markdown](https://github.com/remarkjs/react-markdown) and
[remark-gfm](https://github.com/remarkjs/remark-gfm). Browser tests exercise report
formatting, safe content, mobile overflow and preservation of the existing tool
journeys. Screenshots use explicit offline fixtures, not fresh live Meta output.
