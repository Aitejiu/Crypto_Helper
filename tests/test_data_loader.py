from __future__ import annotations

import pytest

from crypto_helper.core import paths
from crypto_helper.core.evidence_store import collect_all_kol_evidence
from crypto_helper.core.registry_service import list_kols


def test_runtime_data_can_initialize_from_seed(runtime_data_dir: object) -> None:
    del runtime_data_dir
    data_dir = paths.ensure_runtime_data()
    assert data_dir.exists()
    assert (data_dir / "registry" / "kols.json").exists()
    assert (data_dir / "mock" / "trade_calls.json").exists()


def test_crypto_helper_data_dir_env_override_works(runtime_data_dir: object) -> None:
    assert paths.get_data_dir() == runtime_data_dir


def test_default_data_dir_is_repo_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRYPTO_HELPER_DATA_DIR", raising=False)
    assert paths.get_data_dir() == paths.get_project_root() / "crypto_helper_data"


def test_every_kol_has_registry_soul_profile_and_evidence(runtime_data_dir: object) -> None:
    del runtime_data_dir
    for entry in list_kols(status="all"):
        assert paths.resolve_runtime_path(entry.soul_path).exists()
        assert paths.resolve_runtime_path(entry.profile_path).exists()
        assert paths.resolve_runtime_path(entry.evidence_path).exists()


def test_kol_x_has_less_evidence_than_kol_a(runtime_data_dir: object) -> None:
    del runtime_data_dir
    evidence_map = collect_all_kol_evidence()
    assert len(evidence_map["kol_x"]) < len(evidence_map["kol_a"])
