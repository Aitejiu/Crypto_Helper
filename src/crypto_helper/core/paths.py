from __future__ import annotations

import os
import shutil
from pathlib import Path

DATA_ENV_VAR = "CRYPTO_HELPER_DATA_DIR"


def get_seed_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def get_data_dir() -> Path:
    override = os.getenv(DATA_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / "crypto_helper_data"


def ensure_runtime_data() -> Path:
    seed_dir = get_seed_data_dir()
    data_dir = get_data_dir()
    if not data_dir.exists():
        shutil.copytree(seed_dir, data_dir)
    else:
        _copy_missing_seed_content(seed_dir, data_dir)
    for relative_path in ("audit", "reports", "reports/daily"):
        (data_dir / relative_path).mkdir(parents=True, exist_ok=True)
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
