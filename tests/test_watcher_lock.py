from __future__ import annotations

from datetime import UTC, datetime, timedelta

from crypto_helper.agent_runtime.watcher_lock import (
    acquire_watcher_lock,
    get_watcher_lock_status,
    refresh_watcher_lock,
    release_watcher_lock,
)
from crypto_helper.core.data_loader import save_json_path
from crypto_helper.core.paths import get_queue_dir


def test_first_acquire_succeeds(runtime_data_dir: object) -> None:
    del runtime_data_dir

    acquired = acquire_watcher_lock(ttl_seconds=60)
    status = get_watcher_lock_status()

    assert acquired is True
    assert status["locked"] is True
    assert status["expired"] is False
    assert status["pid"] is not None
    assert status["started_at"] is not None
    assert status["heartbeat_at"] is not None
    assert status["ttl_seconds"] == 60


def test_second_acquire_fails_when_lock_not_expired(runtime_data_dir: object) -> None:
    del runtime_data_dir

    assert acquire_watcher_lock(ttl_seconds=60) is True

    assert acquire_watcher_lock(ttl_seconds=60) is False


def test_expired_lock_can_be_acquired(runtime_data_dir: object) -> None:
    del runtime_data_dir
    expired_at = datetime.now(UTC) - timedelta(seconds=120)
    save_json_path(
        get_queue_dir() / ".watcher.lock",
        {
            "pid": 12345,
            "started_at": expired_at.isoformat(),
            "heartbeat_at": expired_at.isoformat(),
            "ttl_seconds": 1,
        },
    )

    assert get_watcher_lock_status()["expired"] is True
    assert acquire_watcher_lock(ttl_seconds=60) is True
    status = get_watcher_lock_status()
    assert status["locked"] is True
    assert status["expired"] is False
    assert status["ttl_seconds"] == 60


def test_release_allows_acquire_again(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert acquire_watcher_lock(ttl_seconds=60) is True

    assert release_watcher_lock() is True

    assert get_watcher_lock_status()["locked"] is False
    assert acquire_watcher_lock(ttl_seconds=60) is True


def test_refresh_updates_active_lock(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert acquire_watcher_lock(ttl_seconds=60) is True
    before = get_watcher_lock_status()["heartbeat_at"]

    assert refresh_watcher_lock() is True

    after = get_watcher_lock_status()["heartbeat_at"]
    assert after is not None
    assert before is not None
    assert after >= before
