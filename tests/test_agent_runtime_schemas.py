from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.agent_runtime import (
    DelegationTask,
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
