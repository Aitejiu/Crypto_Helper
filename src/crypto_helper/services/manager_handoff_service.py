from __future__ import annotations

from crypto_helper.agent_runtime.schemas import DelegationTask, ManagerHandoffResult
from crypto_helper.services.manager_response_service import ManagerResponse


def build_manager_handoff_from_response(
    task: DelegationTask,
    manager_response: ManagerResponse,
) -> ManagerHandoffResult:
    error = None
    if manager_response.status == "failed":
        raw_error = manager_response.payload.get("error")
        error = str(raw_error) if raw_error is not None else "manager_response_failed"

    return ManagerHandoffResult(
        task_id=task.task_id,
        workflow_run_id=task.workflow_run_id,
        workflow_id=task.workflow_id,
        manager_agent="manager-agent",
        status=manager_response.status,
        request_context=task.request_context,
        response_payload=manager_response.payload,
        evidence_refs=manager_response.evidence_refs,
        limitations=manager_response.limitations,
        delivery_hint="reply_to_original_request",
        error=error,
    )
