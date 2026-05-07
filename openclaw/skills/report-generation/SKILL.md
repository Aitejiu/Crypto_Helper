---
name: report-generation
description: Generate readable crypto_helper KOL and market reports. Use when long-form reporting is needed and the output must synthesize tools into narrative text with an Evidence Appendix.
---

# Report Generation

## Purpose

Define how `report-agent` turns crypto_helper tool data into natural, complete, and evidence-backed reports rather than raw JSON dumps.

## When to use

Use this skill when:

- the user requests a KOL weekly report
- the user requests a daily market report
- the answer should be a structured narrative rather than a short tool response

## Required tools

- `crypto_helper_generate_report`
- `crypto_helper_generate_daily_market_report`
- `crypto_helper_get_soul`
- `crypto_helper_get_profile`
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_query_news`
- `crypto_helper_search_evidence`
- `crypto_helper_get_market_summary`
- `crypto_helper_security_review`

## Procedure

1. Run `crypto_helper_security_review` if the request risks slipping into advice or restricted content.
2. Choose KOL report or daily market report flow.
3. Load the core report payload with the matching report tool.
4. Enrich the narrative with SOUL, profile, trade calls, events, opinions, news, and evidence when needed.
5. Rewrite the result into natural, readable analysis instead of pasting raw tool JSON.
6. If the KOL is dynamic and evidence is sparse, explicitly state low confidence.
7. If the KOL is archived, explicitly state archived historical status.
8. Always include an `Evidence Appendix`.

## Safety rules

- `report-agent` is responsible for complete, readable reports.
- Reports must not be simple raw tool JSON concatenation.
- All reports must contain an `Evidence Appendix`.
- KOL reports must contain:
  `KOL summary`, `SOUL summary`, `active symbols`, `recent trade calls`, `recent events`, `opinion summary`, `reliability`, `limitations`, `Evidence Appendix`
- Daily market reports must contain:
  `top symbols`, `important trade calls`, `recent events`, `market news`, `KOL opinions`, `limitations`, `Evidence Appendix`
- Dynamic KOL reports with sparse evidence must state low confidence.
- Archived KOL reports must state archived status.
- Never provide direct investment advice.
- Never make unsupported claims without evidence.

## Required output format

- report title
- readable narrative sections
- explicit limitations
- `Evidence Appendix`
