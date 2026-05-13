from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from crypto_helper.agent_runtime import openclaw_wakeup
from crypto_helper.agent_runtime.queue import enqueue_task
from crypto_helper.agent_runtime.queue_watcher import watch_queue
from crypto_helper.agent_runtime.schemas import DelegationTask, QueueStatus
from crypto_helper.agent_runtime.watcher_lock import acquire_watcher_lock
from crypto_helper.models.common import DomainError
from crypto_helper.request_context import RequestContext


def test_empty_queue_once_does_not_wake(
    runtime_data_dir: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del runtime_data_dir
    wakeups: list[dict[str, Any]] = []

    monkeypatch.setattr(openclaw_wakeup, "wake_queue_dispatcher_agent", lambda: wakeups.append({}))

    result = watch_queue(once=True)

    assert result["status"] == "empty"
    assert result["wakeups_count"] == 0
    assert wakeups == []
    assert result["lock_released"] is True


def test_non_empty_queue_once_wakes_dispatcher(
    runtime_data_dir: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_wake_once"))

    def fake_wake() -> dict[str, Any]:
        return {"ok": True, "result": {"processed_count": 1}}

    monkeypatch.setattr(openclaw_wakeup, "wake_queue_dispatcher_agent", fake_wake)

    result = watch_queue(once=True)

    assert result["status"] == "woke"
    assert result["wakeups_count"] == 1
    assert result["wakeups"][0]["ok"] is True
    assert result["queue_counts"]["pending"] == 1


def test_lock_active_skips_watcher(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert acquire_watcher_lock(ttl_seconds=60) is True

    with pytest.raises(DomainError) as exc_info:
        watch_queue(once=True)

    assert exc_info.value.code == "QUEUE_WATCHER_LOCK_ACTIVE"
    assert exc_info.value.metadata["status"] == "skipped"


def test_cooldown_limits_wakeups(
    runtime_data_dir: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del runtime_data_dir
    enqueue_task(_build_task("task_cooldown"))
    wakeups: list[dict[str, Any]] = []
    sleeps: list[float] = []
    clock_values = iter([0.0, 0.0, 1.0, 11.0, 11.0])

    def fake_wake() -> dict[str, Any]:
        wakeups.append({"ok": True})
        return {"ok": True}

    monkeypatch.setattr(openclaw_wakeup, "wake_queue_dispatcher_agent", fake_wake)

    result = watch_queue(
        poll_interval=0.5,
        cooldown=10,
        once=False,
        max_wakeups=2,
        sleep_fn=sleeps.append,
        monotonic_fn=lambda: next(clock_values),
    )

    assert result["status"] == "max_wakeups_reached"
    assert result["wakeups_count"] == 2
    assert len(wakeups) == 2
    assert sleeps == [0.5, 0.5]


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
