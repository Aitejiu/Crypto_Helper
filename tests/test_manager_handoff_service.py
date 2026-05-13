from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.agent_runtime.schemas import DelegationTask, QueueStatus
from crypto_helper.request_context import RequestContext
from crypto_helper.services.manager_handoff_service import (
    build_manager_handoff_from_response,
)
from crypto_helper.services.manager_response_service import ManagerResponse


def test_persona_task_builds_manager_handoff() -> None:
    task = _build_task("kol_persona", "persona-runtime-agent")
    response = ManagerResponse(
        workflow_id=task.workflow_id,
        target_agent=task.target_agent,
        status="completed",
        payload={"answer": "historical simulation", "confidence": 0.78},
        evidence_refs=[{"evidence_id": "ev_1"}],
        limitations=["historical only"],
    )

    handoff = build_manager_handoff_from_response(task, response)

    assert handoff.manager_agent == "manager-agent"
    assert handoff.task_id == task.task_id
    assert handoff.workflow_run_id == task.workflow_run_id
    assert handoff.workflow_id == "kol_persona"
    assert handoff.response_payload["answer"] == "historical simulation"
    assert handoff.evidence_refs[0]["evidence_id"] == "ev_1"
    assert handoff.limitations == ["historical only"]
    assert handoff.delivery_hint == "reply_to_original_request"


def test_report_task_builds_manager_handoff() -> None:
    task = _build_task("kol_report", "report-agent")
    response = ManagerResponse(
        workflow_id=task.workflow_id,
        target_agent=task.target_agent,
        status="completed",
        payload={"markdown": "# Report\n\n## Evidence Appendix"},
        evidence_refs=[{"evidence_id": "ev_report"}],
        limitations=[],
    )

    handoff = build_manager_handoff_from_response(task, response)

    assert handoff.status == "completed"
    assert handoff.workflow_id == "kol_report"
    assert "Evidence Appendix" in handoff.response_payload["markdown"]
    assert handoff.evidence_refs == [{"evidence_id": "ev_report"}]


def test_failed_manager_response_builds_failed_handoff() -> None:
    task = _build_task("kol_report", "report-agent")
    response = ManagerResponse(
        workflow_id=task.workflow_id,
        target_agent=task.target_agent,
        status="failed",
        payload={"error": "worker_failed"},
        evidence_refs=[],
        limitations=["Worker execution failed."],
    )

    handoff = build_manager_handoff_from_response(task, response)

    assert handoff.status == "failed"
    assert handoff.response_payload["error"] == "worker_failed"
    assert handoff.error == "worker_failed"
    assert handoff.limitations == ["Worker execution failed."]


def test_manager_handoff_preserves_request_context() -> None:
    task = _build_task("kol_persona", "persona-runtime-agent")
    response = ManagerResponse(
        workflow_id=task.workflow_id,
        target_agent=task.target_agent,
        status="completed",
        payload={"answer": "historical simulation"},
    )

    handoff = build_manager_handoff_from_response(task, response)

    assert handoff.request_context == task.request_context
    assert handoff.request_context.channel == "discord"
    assert handoff.request_context.guild_id == "guild-1"
    assert handoff.request_context.chat_id == "chat-1"
    assert handoff.request_context.message_id == "message-1"


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
            message_id="message-1",
            visibility="public",
        ),
        inputs={},
        suggested_tools=[],
        priority=10,
        status=QueueStatus.PENDING,
    )
