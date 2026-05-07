---
name: kol-soul-maintenance
description: Maintain crypto_helper KOL SOUL state with evidence-backed mock patches. Use when recent behavior suggests the SOUL should be updated, reviewed, or applied without violating hard identity and safety rules.
---

# KOL SOUL Maintenance

Use this skill when the system should evolve a KOL SOUL from new evidence.

## Primary Tools

- `crypto_helper_get_soul`
- `crypto_helper_generate_soul_patch_mock`
- `crypto_helper_apply_soul_patch_mock`
- Optional evidence support:
  `crypto_helper_search_evidence`
  `crypto_helper_query_events`

## Patch Workflow

1. Read the current SOUL.
2. Review recent evidence or event patterns.
3. Generate a patch from observed behavior.
4. Inspect confidence and `requires_review`.
5. Apply only when the patch is acceptable for the request.

## Hard Rules

- Never weaken `must_not_claim_real_identity`.
- Keep evidence, confidence, and limitations requirements intact.
- Low-confidence patches require review before application.
- Disabled KOLs should not receive persona-oriented SOUL changes.

## Output Expectations

- State what behavior triggered the patch
- State whether review is required
- Summarize the applied or proposed changes
