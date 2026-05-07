---
name: report-generation
description: Generate long-form crypto_helper reports for one KOL or daily market coverage. Use when the request asks for a weekly KOL report, daily market report, or a structured evidence appendix.
---

# Report Generation

Use this skill for long-form, evidence-backed reporting.

## Primary Tools

- `crypto_helper_generate_report`
- `crypto_helper_generate_daily_market_report`
- Supporting evidence tools when deeper detail is required

## Report Types

- KOL report:
  KOL summary, SOUL summary, active symbols, recent trade calls, recent events, opinion summary, reliability, limitations, Evidence Appendix
- Daily market report:
  Top symbols, important trade calls, recent events, market news, KOL opinions, limitations, Evidence Appendix

## Rules

- Do not output direct investment advice.
- Keep the report grounded in historical mock data.
- Archived KOLs must be labeled as archived.
- Dynamic KOLs with limited evidence must be labeled low confidence.
- Always preserve an `Evidence Appendix`.

## Working Style

1. Generate the base report with the report tool.
2. If the user asks follow-up detail, retrieve specific evidence rather than rewriting from memory.
