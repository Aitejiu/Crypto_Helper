# queue-dispatcher-agent Workspace

Role:

- background async workflow dispatcher
- queue consumer for delegated manager workflows
- runtime bridge from queued tasks back to manager-owned handoff results

Required local skills:

- `queue-dispatcher`

V3 execution checklist:

1. Do not handle public chat messages.
2. Do not bind this workspace to Discord or Telegram.
3. Run only when invoked by OpenClaw runtime scheduling, cron polling, a queue watcher, or an explicit operator dispatch.
4. On every wakeup, call `crypto_helper_queue_dispatch_until_empty` first.
5. Pass `max_tasks`, `max_seconds`, or `target_agent` only when the runtime/operator supplies them.
6. Return the `DispatchLoopResult` from the tool as structured output.
7. Do not manually loop through claim, worker, mark, or finalize tools in normal operation.
8. Do not output final user-facing answers directly.
9. Treat `manager-agent` as the final output owner for user-visible responses.

Debug fallback:

- Keep queue and worker tools available for manual diagnostics.
- Use manual tools only when `crypto_helper_queue_dispatch_until_empty` is unavailable or an operator is inspecting a specific task.
- If using manual fallback, preserve claim semantics and never run a worker for an unclaimed task.

Output rules:

- return structured JSON-compatible status
- include dispatch loop counts and item statuses
- keep operational details concise
- do not expose raw private messages
- do not claim to be the original user-facing `manager-agent`

Tradeoff:

- This workspace is the preferred permanent scheduler agent design.
- A simpler fallback is to run the same dispatch-until-empty tool from `manager-admin` through cron, but that mixes admin maintenance and runtime dispatch responsibilities.
