from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.agent_runtime import (
    DelegationTask,
    DispatchLoopItem,
    DispatchLoopResult,
    ManagerHandoffResult,
    QueueStatus,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.request_context import RequestContext


def test_delegation_task_round_trips() -> None:
    task = DelegationTask(
        task_id="task_1",
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        workflow_run_id="run_1",
        workflow_id="kol_persona",
        source_agent="manager-agent",
        target_agent="persona-runtime-agent",
        request_context=RequestContext(
            channel="discord",
            guild_id="guild-1",
            chat_id="chat-1",
            user_id="user-1",
            visibility="public",
        ),
        inputs={"kol_query": "KOL_A", "topic": "BTC reclaim"},
        suggested_tools=["crypto_helper_get_soul", "crypto_helper_search_evidence"],
        priority=10,
        status=QueueStatus.PENDING,
    )

    payload = task.model_dump(mode="json")
    restored = DelegationTask.model_validate(payload)

    assert restored.task_id == "task_1"
    assert restored.target_agent == "persona-runtime-agent"
    assert restored.request_context.chat_id == "chat-1"


def test_worker_execution_result_round_trips() -> None:
    result = WorkerExecutionResult(
        task_id="task_1",
        target_agent="report-agent",
        status=WorkerExecutionStatus.COMPLETED,
        output_payload={"title": "report"},
        evidence_refs=[{"evidence_id": "ev_1"}],
        limitations=["historical only"],
        completed_at=datetime(2026, 5, 13, 12, 5, tzinfo=UTC),
    )

    payload = result.model_dump(mode="json")
    restored = WorkerExecutionResult.model_validate(payload)

    assert restored.status == WorkerExecutionStatus.COMPLETED
    assert restored.output_payload["title"] == "report"
    assert restored.evidence_refs[0]["evidence_id"] == "ev_1"


def test_dispatch_loop_result_supports_empty_queue() -> None:
    result = DispatchLoopResult(queue_empty=True)

    payload = result.model_dump(mode="json")
    restored = DispatchLoopResult.model_validate(payload)

    assert restored.queue_empty is True
    assert restored.processed_count == 0
    assert restored.failed_count == 0
    assert restored.items == []


def test_dispatch_loop_result_supports_partial_failure() -> None:
    result = DispatchLoopResult(
        processed_count=2,
        failed_count=1,
        queue_empty=False,
        items=[
            DispatchLoopItem(
                task_id="task_1",
                workflow_id="kol_persona",
                target_agent="persona-runtime-agent",
                worker_status=WorkerExecutionStatus.COMPLETED.value,
                queue_status=QueueStatus.DONE,
                manager_response_status="completed",
                manager_handoff_status="ready",
            ),
            DispatchLoopItem(
                task_id="task_2",
                workflow_id="kol_report",
                target_agent="report-agent",
                worker_status=WorkerExecutionStatus.FAILED.value,
                queue_status=QueueStatus.FAILED,
                manager_response_status="failed",
                manager_handoff_status="failed",
                error="worker failed",
            ),
        ],
        limitations=["One task failed."],
    )

    payload = result.model_dump(mode="json")
    restored = DispatchLoopResult.model_validate(payload)

    assert restored.processed_count == 2
    assert restored.failed_count == 1
    assert restored.items[0].queue_status == QueueStatus.DONE
    assert restored.items[1].error == "worker failed"


def test_manager_handoff_result_preserves_request_context() -> None:
    handoff = ManagerHandoffResult(
        task_id="task_1",
        workflow_run_id="run_1",
        workflow_id="kol_persona",
        status="completed",
        request_context=RequestContext(
            channel="telegram",
            chat_id="chat-1",
            user_id="user-1",
            message_id="message-1",
            visibility="public",
        ),
        response_payload={"answer": "profile-based simulation"},
        evidence_refs=[{"evidence_id": "ev_1"}],
        limitations=["historical only"],
    )

    payload = handoff.model_dump(mode="json")
    restored = ManagerHandoffResult.model_validate(payload)

    assert restored.manager_agent == "manager-agent"
    assert restored.delivery_hint == "reply_to_original_request"
    assert restored.request_context.channel == "telegram"
    assert restored.request_context.message_id == "message-1"
    assert restored.response_payload["answer"] == "profile-based simulation"
