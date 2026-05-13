from __future__ import annotations

from pathlib import Path

from crypto_helper.agent_runtime.schemas import (
    DelegationTask,
    QueueStatus,
    WorkerExecutionResult,
)
from crypto_helper.core.data_loader import load_json_path, save_json_path
from crypto_helper.core.paths import ensure_runtime_data


def enqueue_task(task: DelegationTask) -> DelegationTask:
    queued = task.model_copy(update={"status": QueueStatus.PENDING})
    save_json_path(_task_path(queued.status, queued.task_id), queued.model_dump(mode="json"))
    return queued


def claim_next_task(target_agent: str | None = None) -> DelegationTask | None:
    for path in _status_dir(QueueStatus.PENDING).glob("*.json"):
        task = DelegationTask.model_validate(load_json_path(path))
        if target_agent is not None and task.target_agent != target_agent:
            continue
        claimed = task.model_copy(update={"status": QueueStatus.PROCESSING})
        path.rename(_task_path(QueueStatus.PROCESSING, claimed.task_id))
        save_json_path(
            _task_path(QueueStatus.PROCESSING, claimed.task_id), claimed.model_dump(mode="json")
        )
        return claimed
    return None


def mark_task_done(task_id: str, result: WorkerExecutionResult) -> None:
    task = _load_task_from_status(QueueStatus.PROCESSING, task_id)
    completed = task.model_copy(update={"status": QueueStatus.DONE})
    processing_path = _task_path(QueueStatus.PROCESSING, task_id)
    done_path = _task_path(QueueStatus.DONE, task_id)
    if processing_path.exists():
        processing_path.unlink()
    save_json_path(done_path, completed.model_dump(mode="json"))
    save_json_path(_result_path(QueueStatus.DONE, task_id), result.model_dump(mode="json"))


def mark_task_failed(task_id: str, error: str) -> None:
    task = _load_task_from_status(QueueStatus.PROCESSING, task_id)
    failed = task.model_copy(update={"status": QueueStatus.FAILED})
    processing_path = _task_path(QueueStatus.PROCESSING, task_id)
    failed_path = _task_path(QueueStatus.FAILED, task_id)
    if processing_path.exists():
        processing_path.unlink()
    save_json_path(failed_path, failed.model_dump(mode="json"))
    save_json_path(
        _result_path(QueueStatus.FAILED, task_id),
        {
            "task_id": task_id,
            "error": error,
            "status": QueueStatus.FAILED.value,
        },
    )


def get_task(task_id: str) -> DelegationTask | None:
    for status in QueueStatus:
        path = _task_path(status, task_id)
        if path.exists():
            return DelegationTask.model_validate(load_json_path(path))
    return None


def list_pending_tasks() -> list[DelegationTask]:
    tasks: list[DelegationTask] = []
    for path in sorted(_status_dir(QueueStatus.PENDING).glob("*.json")):
        tasks.append(DelegationTask.model_validate(load_json_path(path)))
    return tasks


def _queue_root() -> Path:
    return ensure_runtime_data() / "queues"


def _status_dir(status: QueueStatus) -> Path:
    mapping = {
        QueueStatus.PENDING: "pending",
        QueueStatus.PROCESSING: "processing",
        QueueStatus.DONE: "done",
        QueueStatus.FAILED: "failed",
    }
    path = _queue_root() / mapping[status]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _task_path(status: QueueStatus, task_id: str) -> Path:
    return _status_dir(status) / f"{task_id}.json"


def _result_path(status: QueueStatus, task_id: str) -> Path:
    return _status_dir(status) / f"{task_id}.result.json"


def _load_task_from_status(status: QueueStatus, task_id: str) -> DelegationTask:
    path = _task_path(status, task_id)
    return DelegationTask.model_validate(load_json_path(path))
