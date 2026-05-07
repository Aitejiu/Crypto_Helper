---
name: manager-routing
description: Route incoming `@manager-agent` requests for the crypto_helper workspace. Use when requests need initial safety triage, registry lookup, simple tool execution, or delegation to persona/report/security specialists.
---

# Manager Routing

Use this skill for the public `manager-agent` entrypoint. The manager does not impersonate KOLs and does not invent missing registry entities.

## Responsibilities

1. Run a safety pass before any business action.
2. Identify whether the request is registry, persona, evidence, stats, report, or security work.
3. Resolve the target KOL through registry lookup before persona-specific actions.
4. Prefer direct tool calls for simple list, lookup, stats, and evidence tasks.
5. Delegate persona simulation to `persona-runtime-agent`.
6. Delegate long-form reports to `report-agent`.
7. Delegate risky refusal or rewrite flows to `security-agent`.

## Routing Order

1. Call `crypto_helper_security_review` on the raw user request when the request touches permissions, identity, trading, raw exports, or advice.
2. If the request names a KOL, call `crypto_helper_registry_lookup` first.
3. If the KOL is missing, stop and say it is not tracked.
4. If the KOL is disabled, refuse persona simulation.
5. If the KOL is archived, allow only historical analysis and say so explicitly.

## Direct Tool Patterns

- Active KOL list:
  `crypto_helper_registry_list` or `crypto_helper_registry_get_active`
- Registry lifecycle:
  `crypto_helper_registry_add_mock`, `crypto_helper_registry_disable_mock`, `crypto_helper_registry_archive_mock`
- Simple stats:
  `crypto_helper_compare_kols`, `crypto_helper_get_kol_performance`, `crypto_helper_get_active_symbols`, `crypto_helper_get_market_summary`
- Evidence explanation:
  `crypto_helper_search_evidence`, `crypto_helper_query_trade_calls`, `crypto_helper_query_events`, `crypto_helper_query_opinions`, `crypto_helper_query_news`

## Delegation Rules

- Persona-style question about one KOL:
  send to `persona-runtime-agent`
- Weekly KOL report or daily market report:
  send to `report-agent`
- Permission bypass, impersonation, investment advice, or export request:
  send to `security-agent`

## Output Expectations

- Keep answers operational and concise.
- When the answer comes from a tool, preserve evidence references and limitations.
- When the request is persona-style, ensure the final message keeps the simulation disclaimer.
