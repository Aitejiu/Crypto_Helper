from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from crypto_helper.agent_runtime.queue import (
    claim_next_task,
    mark_task_done,
    mark_task_failed,
)
from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)

SUPPORTED_TARGET_AGENTS = {
    "persona-runtime-agent",
    "report-agent",
    "security-agent",
    "manager-admin",
}


def dispatch_next_task(
    target_agent: str | None = None,
) -> tuple[DelegationTask, WorkerExecutionResult] | None:
    task = claim_next_task(target_agent=target_agent)
    if task is None:
        return None
    try:
        result = dispatch_task(task)
    except Exception as exc:
        mark_task_failed(task.task_id, str(exc))
        return (
            task,
            WorkerExecutionResult(
                task_id=task.task_id,
                target_agent=task.target_agent,
                status=WorkerExecutionStatus.FAILED,
                output_payload={},
                completed_at=datetime.now(UTC),
                error=str(exc),
            ),
        )
    mark_task_done(task.task_id, result)
    return task, result


def dispatch_task(task: DelegationTask) -> WorkerExecutionResult:
    worker = _resolve_worker(task.target_agent)
    return worker(task)


def _resolve_worker(target_agent: str) -> Callable[[DelegationTask], WorkerExecutionResult]:
    if target_agent not in SUPPORTED_TARGET_AGENTS:
        raise ValueError(f"Unsupported target agent: {target_agent}")
    return _dispatch_to_worker


def _dispatch_to_worker(task: DelegationTask) -> WorkerExecutionResult:
    raise NotImplementedError(
        f"Worker adapter for target agent {task.target_agent} is not implemented yet."
    )
