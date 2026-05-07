from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

from crypto_helper.core.paths import resolve_runtime_path
from crypto_helper.models.common import DomainError, to_jsonable


def load_json(relative_path: str) -> Any:
    path = resolve_runtime_path(relative_path)
    return load_json_path(path)


def load_json_path(path: Path) -> Any:
    if not path.exists():
        raise DomainError(f"Missing JSON file: {path}", code="DATA_FILE_MISSING")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(relative_path: str, data: Any) -> Path:
    path = resolve_runtime_path(relative_path)
    save_json_path(path, data)
    return path


def save_json_path(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(data), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_yaml(relative_path: str) -> dict[str, Any]:
    path = resolve_runtime_path(relative_path)
    if not path.exists():
        raise DomainError(f"Missing YAML file: {path}", code="DATA_FILE_MISSING")
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise DomainError(f"Unexpected YAML shape: {path}", code="DATA_FORMAT_ERROR")
    return cast(dict[str, Any], loaded)


def save_yaml(relative_path: str, data: dict[str, Any]) -> Path:
    path = resolve_runtime_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
    return path


def append_jsonl(relative_path: str, record: dict[str, Any]) -> Path:
    path = resolve_runtime_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(record), ensure_ascii=False))
        handle.write("\n")
    return path


def load_jsonl(relative_path: str) -> list[dict[str, Any]]:
    path = resolve_runtime_path(relative_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                raise DomainError(f"Unexpected JSONL row in {path}", code="DATA_FORMAT_ERROR")
            rows.append(cast(dict[str, Any], parsed))
    return rows
