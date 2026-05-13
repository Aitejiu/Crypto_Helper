from __future__ import annotations

from collections.abc import Callable
from time import monotonic, sleep
from typing import Any

from crypto_helper.agent_runtime import openclaw_wakeup
from crypto_helper.agent_runtime.queue import get_queue_counts, has_pending_tasks
from crypto_helper.agent_runtime.watcher_lock import (
    acquire_watcher_lock,
    get_watcher_lock_status,
    refresh_watcher_lock,
    release_watcher_lock,
)
from crypto_helper.models.common import DomainError


def watch_queue(
    *,
    poll_interval: float = 2,
    cooldown: float = 5,
    lock_ttl: int = 60,
    once: bool = False,
    max_wakeups: int | None = None,
    sleep_fn: Callable[[float], None] = sleep,
    monotonic_fn: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    if not acquire_watcher_lock(ttl_seconds=lock_ttl):
        raise DomainError(
            "Queue watcher lock is already active.",
            code="QUEUE_WATCHER_LOCK_ACTIVE",
            metadata={
                "status": "skipped",
                "lock": get_watcher_lock_status(),
            },
        )

    wakeups: list[dict[str, Any]] = []
    iterations = 0
    last_wakeup_at: float | None = None
    status = "empty"

    try:
        while True:
            iterations += 1
            refresh_watcher_lock()
            if has_pending_tasks():
                now = monotonic_fn()
                cooldown_remaining = (
                    0.0 if last_wakeup_at is None else cooldown - (now - last_wakeup_at)
                )
                if cooldown_remaining <= 0:
                    wakeups.append(openclaw_wakeup.wake_queue_dispatcher_agent())
                    last_wakeup_at = monotonic_fn()
                    status = "woke"
                    if max_wakeups is not None and len(wakeups) >= max_wakeups:
                        status = "max_wakeups_reached"
                        break
                else:
                    status = "cooldown"
            else:
                status = "empty"

            if once:
                break
            sleep_fn(poll_interval)
    finally:
        release_watcher_lock()

    return {
        "status": status,
        "once": once,
        "iterations": iterations,
        "wakeups_count": len(wakeups),
        "wakeups": wakeups,
        "queue_counts": get_queue_counts(),
        "lock_released": not get_watcher_lock_status()["locked"],
    }
