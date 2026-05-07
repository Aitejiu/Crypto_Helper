from __future__ import annotations

from crypto_helper.core.stats_service import (
    compare_kols,
    get_active_symbols,
    get_kol_performance,
    get_market_summary,
)


def test_compare_eth_kols(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = compare_kols(symbol="ETH", time_range="30d")
    assert any(item.kol_id == "kol_a" for item in result.rankings)
    assert any(item.kol_id == "kol_b" for item in result.rankings)


def test_active_symbols(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = get_active_symbols("KOL_A")
    assert "BTC" in result.metadata["symbols"]


def test_dynamic_kol_sample_size_limitation(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = get_kol_performance("KOL_X", symbol="BTC", time_range="30d")
    assert result.performance is not None
    assert any("sample size" in limitation.lower() for limitation in result.performance.limitations)


def test_archived_disabled_excluded_by_default(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = compare_kols(symbol="BTC", time_range="30d")
    assert all(item.kol_id not in {"kol_old", "kol_disabled"} for item in result.rankings)


def test_market_summary_for_sol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = get_market_summary(symbol="SOL", time_range="1d")
    assert "SOL" in result.metadata["top_symbols"]
