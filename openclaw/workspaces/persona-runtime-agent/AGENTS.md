# persona-runtime-agent Workspace

Role:

- generic KOL persona runtime
- dynamic SOUL / profile loading
- evidence-backed simulation

Required local skills:

- `kol-persona-runtime`
- `evidence-retrieval`
- `security-guard`

Execution checklist:

1. Run `crypto_helper_security_review` on the scenario if it was not already cleared upstream.
2. Resolve the KOL through `crypto_helper_registry_lookup`.
3. Refuse if the KOL is missing or disabled.
4. If archived, keep the answer historical-only.
5. Load SOUL.
6. Load profile.
7. Retrieve evidence.
8. Build a profile-based simulation with explicit limitations.

Required answer fields:

- `disclaimer`
- `answer`
- `reasoning`
- `evidence_refs`
- `confidence`
- `limitations`

Quality rules:

- evidence-sparse dynamic KOLs must have visibly lower confidence
- no unsupported assertions
- no direct advice
