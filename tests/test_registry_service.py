from __future__ import annotations

from crypto_helper.core.registry_service import (
    add_mock_kol,
    archive_kol,
    disable_kol,
    lookup_kol,
)


def test_lookup_by_kol_id(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert lookup_kol("kol_a") is not None


def test_lookup_by_display_name(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert lookup_kol("KOL_A").kol_id == "kol_a"  # type: ignore[union-attr]


def test_lookup_by_alias(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert lookup_kol("AlphaTrend").kol_id == "kol_a"  # type: ignore[union-attr]


def test_lookup_not_found(runtime_data_dir: object) -> None:
    del runtime_data_dir
    assert lookup_kol("KOL_Z") is None


def test_add_mock_kol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = add_mock_kol("KOL_Y", [], ["ETH", "SOL"])
    assert payload["mock_only"] is True
    assert payload["entry"].kol_id == "kol_y"


def test_disable_kol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = disable_kol("KOL_X")
    assert payload["entry"].status.value == "disabled"


def test_archive_kol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    payload = archive_kol("KOL_X")
    assert payload["entry"].status.value == "archived"
