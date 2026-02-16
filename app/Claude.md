\# app/ (Python)



\## Design

\- Router is rule-based (no LLM needed).

\- Workers:

&nbsp; - Analyst: summary/title/category/tags JSON

&nbsp; - Librarian: Supabase upsert, dedupe, retrieval, list/delete/search

&nbsp; - Recommender: metadata-only rerank (explicit request only)



\## Claude prompting rules

\- Strict JSON schema, no extra keys, no commentary

\- Do not send raw full webpage content: send extracted top paragraphs only (<= ~4k chars)



\## Telegram UX

\- Default: send final combined message only

\- Verbose: send step-by-step “character dialogue” messages after each stage



