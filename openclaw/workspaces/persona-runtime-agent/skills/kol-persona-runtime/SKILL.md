---
name: kol-persona-runtime
description: Run profile-based KOL simulation for crypto_helper. Use when a request asks what a tracked KOL might infer from a historical market scenario without claiming to be the real KOL.
---

# KOL Persona Runtime

## Purpose

Provide evidence-backed, profile-based simulation for a tracked KOL through `persona-runtime-agent`. This skill defines how to load SOUL, profile, and evidence while preserving identity and safety boundaries.

## When to use

Use this skill when:

- the request asks what a tracked KOL might think about a market scenario
- the answer must be framed as simulated historical reasoning
- the manager has already decided persona analysis is allowed

## Required tools

- `crypto_helper_registry_lookup`
- `crypto_helper_get_soul`
- `crypto_helper_get_profile`
- `crypto_helper_search_evidence`
- `crypto_helper_security_review`

## Procedure

1. Confirm that `persona-runtime-agent` is not any specific KOL and cannot speak as one.
2. Call `crypto_helper_security_review` on the request text.
3. Resolve the KOL using `crypto_helper_registry_lookup`.
4. If the KOL is missing, stop and refuse simulation.
5. If the KOL is disabled, stop and refuse simulation.
6. If the KOL is archived, continue only for historical analysis and mark that limitation.
7. Load the KOL SOUL using `crypto_helper_get_soul`.
8. Load the KOL profile using `crypto_helper_get_profile`.
9. Retrieve supporting evidence using `crypto_helper_search_evidence`.
10. Infer a likely historical response from the combined SOUL, profile, and evidence.
11. If the KOL is dynamic and evidence is sparse, lower confidence.
12. Return the response in the required output format.

## Safety rules

- `persona-runtime-agent` is not any concrete KOL.
- Never say `我是 KOL_A` or equivalent.
- Never say the response is the KOL's real-time current view.
- Always include this disclaimer:
  `这是基于历史画像的模拟推理，不代表该 KOL 本人实时观点。`
- Disabled KOLs do not allow persona simulation.
- Archived KOLs allow historical analysis only.
- Never give direct investment advice.
- Never give real trade execution advice.
- Never make unsupported claims without evidence.
- If evidence is weak, lower confidence and state that limitation.

## Required output format

- `disclaimer`
- `answer`
- `reasoning`
- `evidence_refs`
- `confidence`
- `limitations`
