from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_helper.models.common import to_jsonable

DATA_ENV_VAR = "CRYPTO_HELPER_DATA_DIR"


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_seed_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def get_data_dir() -> Path:
    override = os.getenv(DATA_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return get_project_root() / "crypto_helper_data"


def get_legacy_home_data_dir() -> Path:
    return Path.home() / "crypto_helper_data"


def get_registry_dir() -> Path:
    return ensure_runtime_data() / "registry"


def get_evidence_dir() -> Path:
    return ensure_runtime_data() / "evidence"


def get_reports_dir() -> Path:
    return ensure_runtime_data() / "reports"


def get_imports_dir() -> Path:
    return ensure_runtime_data() / "imports"


def get_audit_dir() -> Path:
    return ensure_runtime_data() / "audit"


def get_workflow_runs_dir() -> Path:
    return ensure_runtime_data() / "workflow_runs"


def ensure_runtime_data() -> Path:
    seed_dir = get_seed_data_dir()
    data_dir = get_data_dir()
    if not data_dir.exists():
        legacy_dir = get_legacy_home_data_dir()
        if not os.getenv(DATA_ENV_VAR) and legacy_dir.exists() and legacy_dir != data_dir:
            shutil.copytree(legacy_dir, data_dir)
        else:
            shutil.copytree(seed_dir, data_dir)
    else:
        _copy_missing_seed_content(seed_dir, data_dir)
    _ensure_runtime_layout(data_dir)
    return data_dir


def resolve_runtime_path(relative_path: str) -> Path:
    return ensure_runtime_data() / relative_path


def _copy_missing_seed_content(seed_dir: Path, data_dir: Path) -> None:
    for child in seed_dir.iterdir():
        target = data_dir / child.name
        if target.exists():
            continue
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def _ensure_runtime_layout(data_dir: Path) -> None:
    for relative_path in (
        "registry",
        "kols",
        "mock",
        "evidence",
        "evidence/trade_calls",
        "evidence/opinions",
        "evidence/events",
        "evidence/news",
        "reports",
        "reports/imports",
        "reports/daily",
        "reports/kol",
        "imports",
        "imports/pending",
        "imports/failed",
        "imports/processed",
        "audit",
        "workflow_runs",
    ):
        (data_dir / relative_path).mkdir(parents=True, exist_ok=True)
    _ensure_default_registry_files(data_dir)
    _ensure_default_audit_streams(data_dir)
    _ensure_kol_runtime_layout(data_dir)


def _ensure_default_registry_files(data_dir: Path) -> None:
    registry_dir = data_dir / "registry"
    _ensure_json_file(registry_dir / "aliases.json", {"aliases": {}})
    _ensure_json_file(registry_dir / "platforms.json", {"platforms": {}})


def _ensure_default_audit_streams(data_dir: Path) -> None:
    audit_dir = data_dir / "audit"
    for filename in ("registry.jsonl", "import.jsonl", "profile.jsonl", "security.jsonl"):
        path = audit_dir / filename
        path.touch(exist_ok=True)


def _ensure_kol_runtime_layout(data_dir: Path) -> None:
    kols_dir = data_dir / "kols"
    for kol_dir in (path for path in kols_dir.iterdir() if path.is_dir()):
        (kol_dir / "reports" / "history").mkdir(parents=True, exist_ok=True)
        _ensure_json_file(
            kol_dir / "stats.json",
            {
                "kol_id": kol_dir.name,
                "last_updated": _now(),
                "metrics": {},
                "limitations": ["Stats file initialized but not populated yet."],
            },
        )
        _ensure_json_file(
            kol_dir / "evidence_index.json",
            {
                "kol_id": kol_dir.name,
                "evidence_ids": [],
                "last_updated": _now(),
            },
        )
        (kol_dir / "audit.jsonl").touch(exist_ok=True)


def _ensure_json_file(path: Path, payload: Any) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(payload), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()
