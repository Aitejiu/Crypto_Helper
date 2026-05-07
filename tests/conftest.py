from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture()
def runtime_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runtime_dir = tmp_path / "crypto_helper_runtime"
    monkeypatch.setenv("CRYPTO_HELPER_DATA_DIR", str(runtime_dir))
    return runtime_dir


@pytest.fixture()
def cli_runner(runtime_data_dir: Path) -> CliRunner:
    del runtime_data_dir
    return CliRunner()
