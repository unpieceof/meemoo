\# Project: Telegram Memo Bot (Supabase + Python/CrewAI + Claude API)



\## Goal

\- Ingest URLs (web / X / Instagram) -> memo: title, 3 bullets, category, tags

\- Telegram commands: list/search/delete/recommend

\- Minimize tokens and latency.



\## Non-negotiables (Token discipline)

\- Do not reveal chain-of-thought. Be concise.

\- Prefer Serena MCP symbol tools over reading full files.

\- Never read secrets: .env, \*.pem, \*.key, credentials, service role keys.

\- Do not read large files unless explicitly needed; read smallest ranges first.

\- When asked for structured output, return ONLY JSON and follow schema exactly.

\-  출력은 반드시 한국어로 하세요.



\## Pipeline (no debate)

\- 🎯 Router -> 🔍 Analyst -> 📚 Librarian -> 💡 Recommender (ONLY if user explicitly requests recommendations)

\- Agents output JSON only. Telegram “dialogue vibe” is produced by Python formatters, not by LLM.



\## Repo map

\- /app: Python telegram bot + CrewAI orchestration + Claude API calls

\- /supabase: migrations/schema placeholders



\## Serena-first navigation policy

1\) Use Serena tools (find symbol / references / get body)

2\) If insufficient: read smallest relevant range

3\) Only last resort: read whole file

