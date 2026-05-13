from __future__ import annotations

from time import monotonic
from typing import Any

from crypto_helper.agent_runtime.dispatcher import dispatch_next_task
from crypto_helper.agent_runtime.queue import list_pending_tasks
from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    DispatchLoopItem,
    DispatchLoopResult,
    QueueStatus,
)
from crypto_helper.models.common import DomainError, DomainModel
from crypto_helper.services.manager_handoff_service import (
    build_manager_handoff_from_response,
)
from crypto_helper.services.manager_response_service import (
    build_manager_response_from_worker_result,
)
from crypto_helper.services.workflow_run_service import (
    append_tool_call,
    fail_workflow_run,
    finish_workflow_run,
)


class OrchestratedWorkflowResult(DomainModel):
    task: dict[str, Any] | None = None
    worker_result: dict[str, Any] | None = None
    manager_response: dict[str, Any] | None = None
    status: str


def process_next_queued_workflow(target_agent: str | None = None) -> OrchestratedWorkflowResult:
    dispatched = dispatch_next_task(target_agent=target_agent)
    if dispatched is None:
        return OrchestratedWorkflowResult(status="empty")
    task, worker_result = dispatched
    _append_workflow_record(
        task.workflow_run_id,
        {
            "kind": "worker_dispatch",
            "task_id": task.task_id,
            "target_agent": task.target_agent,
            "worker_status": worker_result.status.value,
            "error": worker_result.error,
        },
    )
    manager_response = build_manager_response_from_worker_result(task, worker_result)
    _append_workflow_record(
        task.workflow_run_id,
        {
            "kind": "manager_response",
            "task_id": task.task_id,
            "response_status": manager_response.status,
        },
    )
    if worker_result.error:
        _fail_workflow_record(task.workflow_run_id, worker_result.error)
    else:
        _finish_workflow_record(
            task.workflow_run_id,
            final_status=manager_response.status,
            evidence_refs=manager_response.evidence_refs,
        )
    return OrchestratedWorkflowResult(
        task=task.model_dump(mode="json"),
        worker_result=worker_result.model_dump(mode="json"),
        manager_response=manager_response.model_dump(mode="json"),
        status=manager_response.status,
    )


def process_queued_workflows_until_empty(
    max_tasks: int = 10,
    max_seconds: int = 120,
    target_agent: str | None = None,
) -> DispatchLoopResult:
    started_at = monotonic()
    result = DispatchLoopResult()

    while result.processed_count < max_tasks:
        if monotonic() - started_at >= max_seconds:
            result.max_seconds_reached = True
            break

        dispatched = dispatch_next_task(target_agent=target_agent)
        if dispatched is None:
            result.queue_empty = len(_matching_pending_tasks(target_agent)) == 0
            break

        task, worker_result = dispatched
        manager_response_status = "failed"
        manager_handoff_status = "failed"
        item_error = worker_result.error
        queue_status = QueueStatus.FAILED if worker_result.error else QueueStatus.DONE

        try:
            _append_workflow_record(
                task.workflow_run_id,
                {
                    "kind": "worker_dispatch",
                    "task_id": task.task_id,
                    "target_agent": task.target_agent,
                    "worker_status": worker_result.status.value,
                    "error": worker_result.error,
                },
            )
            manager_response = build_manager_response_from_worker_result(task, worker_result)
            manager_response_status = manager_response.status
            _append_workflow_record(
                task.workflow_run_id,
                {
                    "kind": "manager_response",
                    "task_id": task.task_id,
                    "response_status": manager_response.status,
                },
            )
            manager_handoff = build_manager_handoff_from_response(task, manager_response)
            manager_handoff_status = manager_handoff.status
            _append_workflow_record(
                task.workflow_run_id,
                {
                    "kind": "manager_handoff",
                    "task_id": task.task_id,
                    "handoff_status": manager_handoff.status,
                    "delivery_hint": manager_handoff.delivery_hint,
                },
            )
            if worker_result.error:
                _fail_workflow_record(task.workflow_run_id, worker_result.error)
            else:
                _finish_workflow_record(
                    task.workflow_run_id,
                    final_status=manager_response.status,
                    evidence_refs=manager_response.evidence_refs,
                )
        except Exception as exc:
            item_error = str(exc)
            manager_handoff_status = "failed"

        result.processed_count += 1
        if item_error is not None:
            result.failed_count += 1

        result.items.append(
            DispatchLoopItem(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                target_agent=task.target_agent,
                worker_status=worker_result.status.value,
                queue_status=queue_status,
                manager_response_status=manager_response_status,
                manager_handoff_status=manager_handoff_status,
                error=item_error,
            )
        )

    if result.processed_count >= max_tasks and len(_matching_pending_tasks(target_agent)) > 0:
        result.max_tasks_reached = True
    if not result.queue_empty and not result.max_tasks_reached:
        result.queue_empty = len(_matching_pending_tasks(target_agent)) == 0
    return result


def _matching_pending_tasks(target_agent: str | None) -> list[DelegationTask]:
    tasks = list_pending_tasks()
    if target_agent is None:
        return tasks
    return [task for task in tasks if task.target_agent == target_agent]


def _append_workflow_record(workflow_run_id: str, payload: dict[str, object]) -> None:
    try:
        append_tool_call(workflow_run_id, payload)
    except DomainError:
        return


def _finish_workflow_record(
    workflow_run_id: str,
    *,
    final_status: str,
    evidence_refs: list[dict[str, object]],
) -> None:
    try:
        finish_workflow_run(
            workflow_run_id,
            final_status=final_status,
            evidence_refs=evidence_refs,
        )
    except DomainError:
        return


def _fail_workflow_record(workflow_run_id: str, error: str) -> None:
    try:
        fail_workflow_run(workflow_run_id, error=error)
    except DomainError:
        return
