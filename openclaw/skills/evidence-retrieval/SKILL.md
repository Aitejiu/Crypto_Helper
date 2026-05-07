---
name: evidence-retrieval
description: Retrieve and explain crypto_helper evidence across notes, trade calls, events, opinions, and news. Use when an answer needs supporting references, historical call details, or evidence-backed explanation.
---

# Evidence Retrieval

Use this skill whenever an answer should cite why the system believes a KOL behaved a certain way.

## Primary Tools

- `crypto_helper_search_evidence`
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_query_news`

## Retrieval Order

1. If the request is about a specific KOL, resolve that KOL first through registry.
2. Use `crypto_helper_search_evidence` for broad explanation and keyword matching.
3. Use the specialized query tools when the user asks for concrete call/event/opinion/news records.

## Query Strategy

- Behavior explanation:
  search evidence by KOL + symbol + keyword
- Trading style:
  trade calls + events
- Sentiment or thesis:
  opinions
- Market developments:
  news

## Output Rules

- Prefer the newest, highest-confidence evidence.
- Call out when evidence is thin or partial.
- Do not fabricate sources.
- Preserve `evidence_id`, timestamps, and summary-level references when summarizing.
