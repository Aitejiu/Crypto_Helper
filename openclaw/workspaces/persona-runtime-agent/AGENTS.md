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

1. Receive a structured task instead of raw channel text whenever manager async delegation is enabled.
2. Run `crypto_helper_security_review` on the scenario if it was not already cleared upstream.
3. Resolve the KOL through `crypto_helper_registry_lookup`.
4. Refuse if the KOL is missing or disabled.
5. If archived, keep the answer historical-only.
6. Load SOUL.
7. Load profile.
8. Retrieve evidence.
9. Build a profile-based simulation with explicit limitations.
10. Return a structured worker execution result, not a raw chat reply.

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
