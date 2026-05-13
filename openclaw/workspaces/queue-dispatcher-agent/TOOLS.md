# TOOLS.md

Primary tools for this workspace:

- `crypto_helper_queue_claim_next`
- `crypto_helper_queue_get_task`
- `crypto_helper_queue_mark_done`
- `crypto_helper_queue_mark_failed`
- `crypto_helper_worker_run_persona`
- `crypto_helper_worker_run_report`
- `crypto_helper_worker_run_security`
- `crypto_helper_worker_run_admin`
- `crypto_helper_manager_finalize_task`

Tool usage notes:

- Claim first; never run a worker without a claimed task.
- Use the claimed task's `target_agent` as the only dispatch selector.
- Use one worker tool per claimed task.
- Store the worker result before calling manager finalize.
- Mark failed when target routing is unsupported or worker execution fails.
- Do not call registry, evidence, report, persona, or admin tools directly from this workspace; use the worker tools.
