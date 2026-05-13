# TOOLS.md

Primary V3 tool for this workspace:

- `crypto_helper_queue_dispatch_until_empty`

Use it on every runtime, cron, or watcher wakeup. It owns the loop:

- claim pending tasks
- run matching worker adapters
- store worker results
- build manager handoff records
- stop when the queue is empty or configured limits are reached

Optional parameters:

- `max_tasks`
- `max_seconds`
- `target_agent`

Debug fallback tools:

- `crypto_helper_queue_claim_next`
- `crypto_helper_queue_get_task`
- `crypto_helper_queue_mark_done`
- `crypto_helper_queue_mark_failed`
- `crypto_helper_worker_run_persona`
- `crypto_helper_worker_run_report`
- `crypto_helper_worker_run_security`
- `crypto_helper_worker_run_admin`
- `crypto_helper_manager_finalize_task`
- `crypto_helper_manager_receive_worker_result`

Tool usage notes:

- Do not implement manual loops in this agent prompt.
- Do not use manual queue or worker tools during normal V3 operation.
- Use manual tools only for operator debugging or if the primary dispatch tool is unavailable.
- Do not call registry, evidence, report, persona, or admin tools directly from this workspace.
- Do not access Discord or Telegram tools directly.
- `manager-agent` remains the final user-facing output owner.
