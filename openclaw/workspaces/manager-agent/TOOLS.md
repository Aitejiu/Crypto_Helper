# TOOLS.md

Primary tools for this workspace:

- `crypto_helper_manager_handle_request`
- `crypto_helper_security_review`
- `crypto_helper_registry_lookup`
- `crypto_helper_registry_list`
- `crypto_helper_registry_get_active`
- `crypto_helper_registry_add_mock`
- `crypto_helper_registry_disable_mock`
- `crypto_helper_registry_archive_mock`
- `crypto_helper_compare_kols`
- `crypto_helper_get_kol_performance`
- `crypto_helper_get_active_symbols`
- `crypto_helper_get_market_summary`
- `crypto_helper_search_evidence`

Tool usage notes:

- Prefer `crypto_helper_manager_handle_request` as the first tool call for inbound requests.
- Use `response_mode` from the unified manager tool result to decide direct handling vs delegation.
- `direct_result` means answer immediately from tool output.
- `queue_enqueued` means the request has been converted into an async task and placed into the local queue.
- `delegate_request` means preserve the structured worker handoff payload for downstream async execution.
- Always resolve KOL identity before KOL-specific actions.
- Security review must precede unsafe, administrative, or advice-like requests.
- Do not use persona or report output as if it were generated locally when delegation is required.
- Workflows 12-16 are disabled and must not execute from `manager-agent`.
- For `@manager-agent` requests touching workflows 12-16, return a no-permission response instead of exposing alternate routing.

Repository anchors:

- canonical skills: `openclaw/skills/`
- workspaces: `openclaw/workspaces/`
- Python CLI root: repo root with `uv run crypto-helper`
- privileged workflows: 12, 13, 14, 15, 16
