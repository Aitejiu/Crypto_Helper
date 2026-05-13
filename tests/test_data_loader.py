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
    assert (data_dir / "registry" / "aliases.json").exists()
    assert (data_dir / "registry" / "platforms.json").exists()
    assert (data_dir / "mock" / "trade_calls.json").exists()
    assert (data_dir / "evidence" / "trade_calls").exists()
    assert (data_dir / "imports" / "failed").exists()
    assert (data_dir / "imports" / "processed").exists()
    assert (data_dir / "workflow_runs").exists()
    assert (data_dir / "queues" / "pending").exists()
    assert (data_dir / "queues" / "processing").exists()
    assert (data_dir / "queues" / "done").exists()
    assert (data_dir / "queues" / "failed").exists()
    assert (data_dir / "vector_index").exists()


def test_runtime_layout_creates_default_files(runtime_data_dir: object) -> None:
    del runtime_data_dir
    data_dir = paths.ensure_runtime_data()
    assert (data_dir / "audit" / "registry.jsonl").exists()
    assert (data_dir / "audit" / "import.jsonl").exists()
    assert (data_dir / "audit" / "profile.jsonl").exists()
    assert (data_dir / "audit" / "security.jsonl").exists()
    kol_a_dir = data_dir / "kols" / "kol_a"
    assert (kol_a_dir / "stats.json").exists()
    assert (kol_a_dir / "evidence_index.json").exists()
    assert (kol_a_dir / "reports" / "history").exists()
    assert (kol_a_dir / "audit.jsonl").exists()


def test_crypto_helper_data_dir_env_override_works(runtime_data_dir: object) -> None:
    assert paths.get_data_dir() == runtime_data_dir


def test_default_data_dir_is_repo_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRYPTO_HELPER_DATA_DIR", raising=False)
    assert paths.get_data_dir() == paths.get_project_root() / "crypto_helper_data"


def test_vector_index_path_helpers(runtime_data_dir: object) -> None:
    del runtime_data_dir
    vector_dir = paths.get_vector_index_dir()
    assert vector_dir == paths.ensure_runtime_data() / "vector_index"
    assert paths.resolve_vector_index_path("chroma/index") == vector_dir / "chroma/index"


def test_queue_path_helpers(runtime_data_dir: object) -> None:
    del runtime_data_dir
    queue_dir = paths.get_queue_dir()
    assert queue_dir == paths.ensure_runtime_data() / "queues"
    assert paths.resolve_queue_path("pending/task_1.json") == queue_dir / "pending/task_1.json"


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
