---
name: registry-management
description: Manage the crypto_helper KOL registry lifecycle. Use when the request asks to list KOLs, look up aliases, add a dynamic KOL, disable one, archive one, or explain registry state.
---

# Registry Management

Use this skill for KOL lifecycle and lookup operations.

## Primary Tools

- `crypto_helper_registry_lookup`
- `crypto_helper_registry_list`
- `crypto_helper_registry_get_active`
- `crypto_helper_registry_add_mock`
- `crypto_helper_registry_disable_mock`
- `crypto_helper_registry_archive_mock`

## Rules

- Lookup must support KOL id, display name, and alias.
- Missing KOLs must stay missing; do not invent entries.
- Adding a KOL creates a dynamic mock KOL only.
- Disabling or archiving never hard-deletes history.
- Archived KOLs can remain available for historical analysis.

## Common Flows

- List tracked KOLs:
  use `crypto_helper_registry_get_active`
- Explain a name or alias:
  use `crypto_helper_registry_lookup`
- Add a new watchlist KOL:
  use `crypto_helper_registry_add_mock`
- Remove from active use without deletion:
  disable or archive through the matching tool

## Output Expectations

- Return the registry result clearly
- Preserve lifecycle status
- When a change is made, note that it is `mock_only`
