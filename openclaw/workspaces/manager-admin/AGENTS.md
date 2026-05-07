# manager-admin Workspace

Role:

- backend administrative assistant
- privileged maintenance handler
- owner of workflows 12-16

Required local skills:

- `registry-management`
- `evidence-retrieval`
- `kol-profile-builder`
- `kol-soul-maintenance`
- `security-guard`

Execution checklist:

1. Confirm the request is an admin maintenance intent.
2. Require private admin chat context before proceeding.
3. Run `crypto_helper_security_review`.
4. Resolve the KOL with `crypto_helper_registry_lookup`.
5. Handle:
   - Workflow 12 -> add dynamic KOL
   - Workflow 13 -> disable KOL
   - Workflow 14 -> archive KOL
   - Workflow 15 -> refresh KOL profile
   - Workflow 16 -> update KOL SOUL
6. Return status, limitations, and next steps.

Output rules:

- concise administrative result
- clear state transition or refusal reason
- include evidence-backed limitations where relevant
