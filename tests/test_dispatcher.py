from __future__ import annotations

from datetime import UTC, datetime

import pytest

from crypto_helper.agent_runtime.dispatcher import dispatch_next_task, dispatch_task
from crypto_helper.agent_runtime.queue import enqueue_task, get_task
from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    QueueStatus,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.request_context import RequestContext


def test_dispatch_next_task_claims_and_runs(
    monkeypatch: pytest.MonkeyPatch, runtime_data_dir: object
) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_dispatch_1", "persona-runtime-agent"))

    def fake_worker(task: DelegationTask) -> WorkerExecutionResult:
        return WorkerExecutionResult(
            task_id=task.task_id,
            target_agent=task.target_agent,
            status=WorkerExecutionStatus.COMPLETED,
            output_payload={"answer": "ok"},
            completed_at=datetime(2026, 5, 13, 13, 0, tzinfo=UTC),
        )

    monkeypatch.setattr("crypto_helper.agent_runtime.dispatcher._dispatch_to_worker", fake_worker)

    outcome = dispatch_next_task()

    assert outcome is not None
    task, result = outcome
    assert task.task_id == "task_dispatch_1"
    assert result.status == WorkerExecutionStatus.COMPLETED
    assert get_task(task.task_id) is not None
    assert get_task(task.task_id).status == QueueStatus.DONE  # type: ignore[union-attr]


def test_dispatch_task_rejects_unsupported_target(runtime_data_dir: object) -> None:
    del runtime_data_dir
    with pytest.raises(ValueError):
        dispatch_task(_build_task("task_dispatch_2", "unknown-agent"))


def test_dispatch_next_task_failure_moves_to_failed(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_dispatch_3", "report-agent"))

    def failing_worker(task: DelegationTask) -> WorkerExecutionResult:
        raise RuntimeError(f"worker failed: {task.task_id}")

    monkeypatch.setattr(
        "crypto_helper.agent_runtime.dispatcher._dispatch_to_worker", failing_worker
    )

    outcome = dispatch_next_task()

    assert outcome is not None
    task, result = outcome
    assert task.task_id == "task_dispatch_3"
    assert result.status == WorkerExecutionStatus.FAILED
    assert get_task(task.task_id) is not None
    assert get_task(task.task_id).status == QueueStatus.FAILED  # type: ignore[union-attr]


def _build_task(task_id: str, target_agent: str) -> DelegationTask:
    return DelegationTask(
        task_id=task_id,
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        workflow_run_id=f"run_{task_id}",
        workflow_id="kol_persona",
        source_agent="manager-agent",
        target_agent=target_agent,
        request_context=RequestContext(
            channel="discord",
            guild_id="guild-1",
            chat_id="chat-1",
            user_id="user-1",
            visibility="public",
        ),
        inputs={"kol_query": "KOL_A"},
        suggested_tools=["crypto_helper_search_evidence"],
        priority=10,
        status=QueueStatus.PENDING,
    )
