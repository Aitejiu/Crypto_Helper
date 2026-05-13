from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    QueueStatus,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.request_context import RequestContext
from crypto_helper.services.manager_response_service import (
    build_manager_response_from_worker_result,
)


def test_persona_worker_result_builds_manager_response() -> None:
    task = _build_task("kol_persona", "persona-runtime-agent")
    result = WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.COMPLETED,
        output_payload={"answer": "historical simulation", "confidence": 0.78},
        evidence_refs=[{"evidence_id": "ev_1"}],
        limitations=["historical only"],
        completed_at=datetime(2026, 5, 13, 13, 0, tzinfo=UTC),
    )

    response = build_manager_response_from_worker_result(task, result)

    assert response.status == "completed"
    assert response.payload["answer"] == "historical simulation"
    assert response.evidence_refs[0]["evidence_id"] == "ev_1"


def test_report_worker_result_builds_manager_response() -> None:
    task = _build_task("kol_report", "report-agent")
    result = WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.COMPLETED,
        output_payload={"markdown": "# Report\n\n## Evidence Appendix"},
        evidence_refs=[{"evidence_id": "ev_2"}],
        limitations=[],
        completed_at=datetime(2026, 5, 13, 13, 0, tzinfo=UTC),
    )

    response = build_manager_response_from_worker_result(task, result)

    assert response.status == "completed"
    assert "Evidence Appendix" in response.payload["markdown"]


def test_security_worker_result_builds_blocked_response() -> None:
    task = _build_task("security_refusal", "security-agent")
    result = WorkerExecutionResult(
        task_id=task.task_id,
        target_agent=task.target_agent,
        status=WorkerExecutionStatus.BLOCKED,
        output_payload={
            "reason": "not allowed",
            "rewritten_safe_intent": "ask for historical analysis",
        },
        evidence_refs=[],
        limitations=["not allowed"],
        completed_at=datetime(2026, 5, 13, 13, 0, tzinfo=UTC),
    )

    response = build_manager_response_from_worker_result(task, result)

    assert response.status == "blocked"
    assert response.payload["reason"] == "not allowed"


def _build_task(workflow_id: str, target_agent: str) -> DelegationTask:
    return DelegationTask(
        task_id=f"task_{workflow_id}",
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        workflow_run_id=f"run_{workflow_id}",
        workflow_id=workflow_id,
        source_agent="manager-agent",
        target_agent=target_agent,
        request_context=RequestContext(
            channel="discord",
            guild_id="guild-1",
            chat_id="chat-1",
            user_id="user-1",
            visibility="public",
        ),
        inputs={},
        suggested_tools=[],
        priority=10,
        status=QueueStatus.PENDING,
    )
