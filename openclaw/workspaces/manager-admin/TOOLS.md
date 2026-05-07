# TOOLS.md

Primary tools for this workspace:

- `crypto_helper_security_review`
- `crypto_helper_registry_lookup`
- `crypto_helper_registry_add_mock`
- `crypto_helper_registry_disable_mock`
- `crypto_helper_registry_archive_mock`
- `crypto_helper_get_profile`
- `crypto_helper_query_trade_calls`
- `crypto_helper_query_events`
- `crypto_helper_query_opinions`
- `crypto_helper_search_evidence`
- `crypto_helper_get_soul`
- `crypto_helper_generate_soul_patch_mock`
- `crypto_helper_apply_soul_patch_mock`

Tool usage notes:

- This agent should only be reached through a private admin binding.
- Workflow 12-16 are the primary scope of this agent.
- Always security-review before state change.
- Evidence-backed maintenance is required for profile and SOUL updates.
