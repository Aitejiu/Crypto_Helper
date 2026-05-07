---
name: stats-query
description: Answer historical performance and market summary questions for crypto_helper. Use when the user asks which KOL performed best, active symbols, comparative rankings, or daily symbol-level market summaries.
---

# Stats Query

This skill is for historical measurement only. It does not provide direct investment advice.

## Primary Tools

- `crypto_helper_compare_kols`
- `crypto_helper_get_kol_performance`
- `crypto_helper_get_active_symbols`
- `crypto_helper_get_market_summary`

## Use Cases

- "最近 30 天哪个 KOL 对 ETH 判断最准？"
- "KOL_A 最近 90 天 BTC 表现怎样？"
- "KOL_A 现在主要覆盖哪些币？"
- "今天 SOL 有哪些重要市场变化？"

## Interpretation Rules

- Exclude disabled and archived KOLs unless the user explicitly asks for historical archived context.
- Dynamic KOLs can appear in rankings, but sparse samples must be treated as lower confidence.
- If sample size is below three, highlight that the ranking is unstable.
- Always present results as historical stats, not future advice.

## Response Shape

- Title or headline answer
- Core metric or ranking
- Sample size
- Evidence references
- Limitations
