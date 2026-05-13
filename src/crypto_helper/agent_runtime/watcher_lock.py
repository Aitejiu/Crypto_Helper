from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from crypto_helper.core.data_loader import load_json_path, save_json_path
from crypto_helper.core.paths import get_queue_dir

LOCK_FILENAME = ".watcher.lock"
DEFAULT_TTL_SECONDS = 60


def acquire_watcher_lock(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    lock_path = _lock_path()
    existing = _load_lock_payload(lock_path)
    if existing is not None and not _is_expired(existing):
        return False
    _write_lock(lock_path, ttl_seconds=ttl_seconds, started_at=_now())
    return True


def refresh_watcher_lock() -> bool:
    lock_path = _lock_path()
    existing = _load_lock_payload(lock_path)
    if existing is None or _is_expired(existing):
        return False
    refreshed = {
        **existing,
        "pid": int(existing.get("pid", os.getpid())),
        "heartbeat_at": _now().isoformat(),
        "ttl_seconds": int(existing.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
    }
    save_json_path(lock_path, refreshed)
    return True


def release_watcher_lock() -> bool:
    lock_path = _lock_path()
    if not lock_path.exists():
        return False
    lock_path.unlink()
    return True


def get_watcher_lock_status() -> dict[str, Any]:
    lock_path = _lock_path()
    payload = _load_lock_payload(lock_path)
    if payload is None:
        return {
            "locked": False,
            "expired": False,
            "path": str(lock_path),
            "pid": None,
            "started_at": None,
            "heartbeat_at": None,
            "ttl_seconds": None,
        }
    return {
        "locked": True,
        "expired": _is_expired(payload),
        "path": str(lock_path),
        "pid": payload.get("pid"),
        "started_at": payload.get("started_at"),
        "heartbeat_at": payload.get("heartbeat_at"),
        "ttl_seconds": payload.get("ttl_seconds"),
    }


def _lock_path() -> Path:
    return get_queue_dir() / LOCK_FILENAME


def _write_lock(lock_path: Path, *, ttl_seconds: int, started_at: datetime) -> None:
    payload = {
        "pid": os.getpid(),
        "started_at": started_at.isoformat(),
        "heartbeat_at": started_at.isoformat(),
        "ttl_seconds": ttl_seconds,
    }
    save_json_path(lock_path, payload)


def _load_lock_payload(lock_path: Path) -> dict[str, Any] | None:
    if not lock_path.exists():
        return None
    try:
        loaded = load_json_path(lock_path)
    except Exception:
        return None
    if not isinstance(loaded, dict):
        return None
    return cast(dict[str, Any], loaded)


def _is_expired(payload: dict[str, Any]) -> bool:
    heartbeat_at = _parse_datetime(payload.get("heartbeat_at"))
    ttl_seconds = _parse_ttl(payload.get("ttl_seconds"))
    if heartbeat_at is None:
        return True
    return _now() >= heartbeat_at + timedelta(seconds=ttl_seconds)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_ttl(value: object) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return DEFAULT_TTL_SECONDS


def _now() -> datetime:
    return datetime.now(UTC)
