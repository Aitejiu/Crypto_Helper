from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.agent_runtime.queue import (
    claim_next_task,
    enqueue_task,
    get_queue_counts,
    get_task,
    has_pending_tasks,
    list_pending_tasks,
    mark_task_done,
    mark_task_failed,
)
from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    QueueStatus,
    WorkerExecutionResult,
    WorkerExecutionStatus,
)
from crypto_helper.request_context import RequestContext


def test_enqueue_task_can_be_read_back(runtime_data_dir: object) -> None:
    del runtime_data_dir
    task = enqueue_task(_build_task("task_1"))

    restored = get_task(task.task_id)

    assert restored is not None
    assert restored.task_id == "task_1"
    assert restored.status == QueueStatus.PENDING


def test_empty_queue_counts_are_zero(runtime_data_dir: object) -> None:
    del runtime_data_dir

    assert get_queue_counts() == {
        "pending": 0,
        "processing": 0,
        "done": 0,
        "failed": 0,
    }
    assert has_pending_tasks() is False


def test_enqueue_increases_pending_count(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_pending_count"))

    counts = get_queue_counts()

    assert counts["pending"] == 1
    assert counts["processing"] == 0
    assert has_pending_tasks() is True


def test_claim_increases_processing_count(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_processing_count"))

    claim_next_task()
    counts = get_queue_counts()

    assert counts["pending"] == 0
    assert counts["processing"] == 1
    assert has_pending_tasks() is False


def test_claim_moves_task_to_processing(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_2"))

    claimed = claim_next_task()

    assert claimed is not None
    assert claimed.task_id == "task_2"
    assert claimed.status == QueueStatus.PROCESSING


def test_mark_task_done_moves_task(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_3"))
    claim_next_task()

    mark_task_done(
        "task_3",
        WorkerExecutionResult(
            task_id="task_3",
            target_agent="persona-runtime-agent",
            status=WorkerExecutionStatus.COMPLETED,
            output_payload={"answer": "ok"},
            completed_at=datetime(2026, 5, 13, 12, 5, tzinfo=UTC),
        ),
    )

    restored = get_task("task_3")
    assert restored is not None
    assert restored.status == QueueStatus.DONE


def test_mark_task_failed_moves_task(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_4"))
    claim_next_task()

    mark_task_failed("task_4", "boom")

    restored = get_task("task_4")
    assert restored is not None
    assert restored.status == QueueStatus.FAILED


def test_done_and_failed_counts_are_correct(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_done_count"))
    claim_next_task()
    mark_task_done(
        "task_done_count",
        WorkerExecutionResult(
            task_id="task_done_count",
            target_agent="persona-runtime-agent",
            status=WorkerExecutionStatus.COMPLETED,
            completed_at=datetime(2026, 5, 13, 12, 5, tzinfo=UTC),
        ),
    )
    enqueue_task(_build_task("task_failed_count"))
    claim_next_task()
    mark_task_failed("task_failed_count", "boom")

    counts = get_queue_counts()

    assert counts == {
        "pending": 0,
        "processing": 0,
        "done": 1,
        "failed": 1,
    }


def test_list_pending_tasks(runtime_data_dir: object) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_5"))
    enqueue_task(_build_task("task_6"))

    tasks = list_pending_tasks()

    assert {task.task_id for task in tasks} == {"task_5", "task_6"}


def _build_task(task_id: str) -> DelegationTask:
    return DelegationTask(
        task_id=task_id,
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        workflow_run_id=f"run_{task_id}",
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
        inputs={"kol_query": "KOL_A"},
        suggested_tools=["crypto_helper_search_evidence"],
        priority=10,
        status=QueueStatus.PENDING,
    )
