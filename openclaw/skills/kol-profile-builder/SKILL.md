---
name: kol-profile-builder
description: Refresh and rebuild crypto_helper KOL profiles from recent evidence. Use when the request asks to update a KOL's profile, active symbols, trade style, or reliability based on current mock records.
---

# KOL Profile Builder

Use this skill to refresh `profile.json` for a tracked KOL.

## Primary Tool

- `crypto_helper_get_profile`

## Refresh Tool

- `crypto_helper_get_profile` for current snapshot
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_search_evidence`
- `crypto_helper_get_profile` after refresh, or the profile refresh business action when exposed by the agent workflow

## Refresh Pattern

1. Resolve the target KOL through registry.
2. Pull recent trade calls, events, opinions, and evidence.
3. Recompute active symbols, trade style, and reliability.
4. Persist the updated profile through the business-layer refresh flow.
5. Summarize what changed.

## Guardrails

- Do not create a profile for a missing KOL.
- Preserve historical framing for archived KOLs.
- Do not invent evidence or reliability.
