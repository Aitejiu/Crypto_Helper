# TOOLS.md

Primary tools for this workspace:

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

- Always resolve KOL identity before KOL-specific actions.
- Security review must precede unsafe, administrative, or advice-like requests.
- Do not use persona or report output as if it were generated locally when delegation is required.

Repository anchors:

- canonical skills: `openclaw/skills/`
- workspaces: `openclaw/workspaces/`
- Python CLI root: repo root with `uv run crypto-helper`
