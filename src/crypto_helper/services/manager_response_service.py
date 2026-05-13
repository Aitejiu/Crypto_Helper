from __future__ import annotations

from typing import Any

from pydantic import Field

from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.models.common import DomainModel


class ManagerResponse(DomainModel):
    workflow_id: str
    target_agent: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def build_manager_response_from_worker_result(
    task: DelegationTask,
    worker_result: WorkerExecutionResult,
) -> ManagerResponse:
    if worker_result.status == WorkerExecutionStatus.FAILED:
        return ManagerResponse(
            workflow_id=task.workflow_id,
            target_agent=task.target_agent,
            status="failed",
            payload={"error": worker_result.error or "worker_failed"},
            evidence_refs=[],
            limitations=[worker_result.error or "Worker execution failed."],
        )
    if task.workflow_id == "security_refusal":
        return ManagerResponse(
            workflow_id=task.workflow_id,
            target_agent=task.target_agent,
            status="blocked",
            payload=worker_result.output_payload,
            evidence_refs=[],
            limitations=worker_result.limitations,
        )
    if task.workflow_id in {"kol_report", "daily_market_report"}:
        return ManagerResponse(
            workflow_id=task.workflow_id,
            target_agent=task.target_agent,
            status="completed",
            payload=worker_result.output_payload,
            evidence_refs=worker_result.evidence_refs,
            limitations=worker_result.limitations,
        )
    return ManagerResponse(
        workflow_id=task.workflow_id,
        target_agent=task.target_agent,
        status="completed",
        payload=worker_result.output_payload,
        evidence_refs=worker_result.evidence_refs,
        limitations=worker_result.limitations,
    )
