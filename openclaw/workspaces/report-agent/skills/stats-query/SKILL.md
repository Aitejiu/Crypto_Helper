---
name: stats-query
description: Answer historical crypto_helper statistics questions for KOL rankings, performance, active symbols, and market summaries. Use when requests are about historical measurement rather than advice.
---

# Stats Query

## Purpose

Define how agents answer historical performance and market summary questions using crypto_helper stats tools.

## When to use

Use this skill when:

- the user asks which KOL performed best on a symbol
- the user asks for one KOL's historical performance
- the user asks what symbols a KOL actively covers
- the user asks for a market summary built from historical mock data

## Required tools

- `crypto_helper_compare_kols`
- `crypto_helper_get_kol_performance`
- `crypto_helper_get_active_symbols`
- `crypto_helper_get_market_summary`
- `crypto_helper_search_evidence`

## Procedure

1. Decide whether the question is simple or complex.
2. For simple rankings or one-step stats, let `manager-agent` answer directly.
3. For broader multi-part stats synthesis, allow delegation to `report-agent` or a future `stats-agent`.
4. Use the relevant stats tool for the direct metric.
5. Pull supporting evidence references when the answer needs traceability.
6. Exclude archived and disabled KOLs by default.
7. Allow dynamic KOLs in comparisons, but explicitly state sample-risk limitations when applicable.
8. If `sample_size < 3`, mark the result low confidence.

## Safety rules

- Only perform historical statistics, never investment advice.
- Every statistical result must include `sample_size`.
- `sample_size < 3` must be flagged as low confidence.
- Archived and disabled KOLs are excluded by default.
- Dynamic KOLs may participate, but sample insufficiency risk must be stated.
- Statistical conclusions must bind to `evidence_refs`.

## Required output format

- headline answer
- `sample_size`
- key metrics or ranking
- `evidence_refs`
- limitations
