# Queue Dispatcher Skill

Use this skill only for background async delegation queue processing.

## Purpose

The queue dispatcher consumes queued workflow tasks created by `manager-agent`, runs the correct worker adapter, stores the worker result, and asks the manager finalize layer to produce the final manager-facing response payload.

It is not a public chat assistant and must not answer Discord or Telegram users directly.

## Required Flow

1. Claim one task with `crypto_helper_queue_claim_next`.
2. If no task is returned, stop with a no-op status.
3. Inspect the task with `crypto_helper_queue_get_task` when needed.
4. Read `target_agent`.
5. Run exactly one matching worker tool:
   - `persona-runtime-agent` -> `crypto_helper_worker_run_persona`
   - `report-agent` -> `crypto_helper_worker_run_report`
   - `security-agent` -> `crypto_helper_worker_run_security`
   - `manager-admin` -> `crypto_helper_worker_run_admin`
6. If the worker result succeeds, store it with `crypto_helper_queue_mark_done`.
7. If the worker result fails or the target is unsupported, store failure with `crypto_helper_queue_mark_failed`.
8. After a successful mark-done, call `crypto_helper_manager_finalize_task`.
9. Return the finalized response payload as structured JSON for the runtime to deliver.

## Boundaries

- Do not access Discord or Telegram directly.
- Do not invent tasks.
- Do not bypass queue claim semantics.
- Do not execute more than one task per dispatch loop unless explicitly instructed by the runtime.
- Do not call worker tools whose target does not match the claimed task.
- Do not expose raw private messages.

## Expected Output

Return a compact structured result with:

- `task_id`
- `target_agent`
- `worker_status`
- `finalize_status`
- `manager_response`
- `limitations`
