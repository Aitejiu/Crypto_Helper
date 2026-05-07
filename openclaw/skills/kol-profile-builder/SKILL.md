---
name: kol-profile-builder
description: Build or refresh crypto_helper KOL profiles from evidence. Use when a tracked KOL profile needs to be refreshed, summarized, or reconciled against recent trade calls, events, opinions, and evidence.
---

# KOL Profile Builder

## Purpose

Define how a KOL profile is refreshed or rebuilt from evidence rather than intuition.

## When to use

Use this skill when:

- the user asks to refresh a KOL profile
- the system needs to summarize updated active symbols or trade style
- an agent needs a grounded profile-change explanation

## Required tools

- `crypto_helper_registry_lookup`
- `crypto_helper_get_profile`
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_search_evidence`

## Procedure

1. Resolve the KOL with `crypto_helper_registry_lookup`.
2. Load the current profile with `crypto_helper_get_profile`.
3. Query recent trade calls.
4. Query recent trade call events.
5. Query recent opinions.
6. Search broader evidence.
7. Derive or refresh:
   `active_symbols`, `trade_style`, `historical_performance`, `reliability`
8. If the runtime can persist a refresh, use the surrounding business-layer refresh flow.
9. If persistence is not available in the current path, output a structured refresh summary instead.

## Safety rules

- This skill is for refreshing or building a profile from evidence.
- Profile changes must be evidence-based.
- Never modify a profile without evidence.
- Always query trade calls, trade call events, opinions, and evidence.
- Disabled KOLs should not be actively refreshed.
- Archived KOLs allow historical refresh only.

## Required output format

- `active_symbols`
- `trade_style`
- `historical_performance`
- `reliability`
- `evidence_refs`
- `limitations`
