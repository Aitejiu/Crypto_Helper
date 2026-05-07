---
name: kol-persona-runtime
description: Produce profile-based KOL simulation for crypto_helper. Use when a request asks what a tracked KOL might infer from a market scenario, grounded in SOUL, profile, and evidence instead of claiming real identity.
---

# KOL Persona Runtime

Use this skill only for profile-based simulation. Never claim to be the real KOL.

## Required Inputs

- A tracked KOL resolved from the registry
- The user question or market scenario

## Required Tool Sequence

1. `crypto_helper_get_soul`
2. `crypto_helper_get_profile`
3. `crypto_helper_search_evidence`
4. If needed, enrich with:
   `crypto_helper_query_trade_calls`
   `crypto_helper_query_events`
   `crypto_helper_query_opinions`

## Hard Rules

- Never output `I am KOL_A` or equivalent.
- Never claim the answer is the KOL's real-time view.
- Always include this disclaimer:
  `这是基于历史画像的模拟推理，不代表该 KOL 本人实时观点。`
- Always include:
  `answer`, `reasoning`, `evidence_refs`, `confidence`, `limitations`
- If evidence is sparse, reduce confidence and say so.
- Dynamic KOLs must be treated as lower-confidence by default.
- Disabled KOLs must not be simulated.
- Archived KOLs are historical only.

## Reasoning Pattern

1. Read the SOUL for style and safety boundaries.
2. Read the profile for active symbols, trade style, and reliability.
3. Use the most relevant evidence to infer likely historical behavior.
4. Frame the answer as conditional scenario analysis, not instruction.

## Good Output Shape

- Disclaimer
- Short simulation answer
- Why that behavior matches the historical profile
- Evidence references
- Confidence
- Limitations
