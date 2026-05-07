---
name: kol-soul-maintenance
description: Maintain crypto_helper KOL SOUL documents through evidence-backed SoulPatch updates. Use when recent behavior suggests a KOL SOUL should be proposed, reviewed, or applied safely.
---

# KOL SOUL Maintenance

## Purpose

Define how crypto_helper SOUL state is updated through evidence-backed patches rather than direct manual overwrite.

## When to use

Use this skill when:

- the user asks to update a KOL SOUL from recent evidence
- an agent needs to propose or apply a SoulPatch
- a new dynamic KOL needs an initial default SOUL

## Required tools

- `crypto_helper_registry_lookup`
- `crypto_helper_search_evidence`
- `crypto_helper_get_soul`
- `crypto_helper_generate_soul_patch_mock`
- `crypto_helper_apply_soul_patch_mock`

## Procedure

1. Resolve the KOL through `crypto_helper_registry_lookup`.
2. Search relevant evidence for the observed behavior.
3. Load the current SOUL with `crypto_helper_get_soul`.
4. Generate an evidence-backed patch with `crypto_helper_generate_soul_patch_mock`.
5. Normalize the proposed patch into entries containing:
   `field`, `old_value`, `new_value`, `confidence`, `evidence_refs`, `requires_review`, `reason`
6. If confidence is low, set `requires_review=true`.
7. Apply the patch with `crypto_helper_apply_soul_patch_mock` only when allowed.
8. For new KOL creation, ensure a default SOUL exists.

## Safety rules

- SOUL may only change through an evidence-backed SoulPatch.
- Never directly hand-overwrite SOUL as an unsupported shortcut.
- Low-confidence patches must have `requires_review=true`.
- Never change `must_not_claim_real_identity` to `false`.
- Archived KOLs default to historical-only SOUL maintenance.
- Disabled KOLs should not be actively updated by default.

## Required output format

- patch summary
- list of patch entries with:
  `field`, `old_value`, `new_value`, `confidence`, `evidence_refs`, `requires_review`, `reason`
- final application status
- limitations
