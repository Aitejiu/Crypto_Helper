---
name: evidence-retrieval
description: Retrieve, rank, and explain crypto_helper evidence for KOL behavior, trade history, opinions, events, and market news. Use when an answer must be evidence-backed and traceable.
---

# Evidence Retrieval

## Purpose

Define how crypto_helper agents gather and present evidence-backed support for KOL conclusions, historical behavior, and market context.

## When to use

Use this skill when:

- a conclusion must cite evidence references
- the user asks why the system made a KOL inference
- the answer depends on trade calls, events, opinions, or news

## Required tools

- `crypto_helper_search_evidence`
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_query_news`

## Procedure

1. If the request targets a specific KOL, keep the query bound to that KOL.
2. Use `crypto_helper_search_evidence` for broad relevance matching.
3. Use the specialized query tools when the user asks for calls, events, opinions, or news explicitly.
4. Rank evidence by:
   KOL match, symbol match, query keyword match, confidence, timestamp
5. Prefer recent, high-confidence evidence when summarizing.
6. If evidence is insufficient, lower confidence.
7. If evidence remains insufficient, include explicit limitations.
8. Return evidence references with summaries rather than raw private message content.

## Safety rules

- Every conclusion must bind to `evidence_refs`.
- Never fabricate evidence.
- Never mix evidence across KOLs as if it belonged to one KOL.
- If evidence is insufficient, lower confidence.
- If evidence is insufficient, output limitations.
- Never output raw private messages directly; only summarize and cite evidence refs.

## Required output format

- matched evidence summary
- `evidence_refs`
- confidence statement
- limitations when evidence is thin
