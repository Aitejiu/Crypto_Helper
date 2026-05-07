from __future__ import annotations

import pytest

from crypto_helper.core.evidence_store import (
    query_events,
    query_news,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.models.common import DomainError


def test_search_by_kol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = search_evidence(kol_query="KOL_A")
    assert all(item.kol_id == "kol_a" for item in result.items if item.kol_id)


def test_search_by_symbol(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = search_evidence(symbol="SOL")
    assert any(item.symbol == "SOL" for item in result.items)


def test_search_by_query_keyword(runtime_data_dir: object) -> None:
    del runtime_data_dir
    result = search_evidence(kol_query="KOL_A", symbol="BTC", query="invalidation")
    assert any("invalidation" in item.summary.lower() for item in result.items)


def test_query_trade_calls(runtime_data_dir: object) -> None:
    del runtime_data_dir
    calls = query_trade_calls(kol_query="KOL_A", symbol="BTC")
    assert calls


def test_query_events(runtime_data_dir: object) -> None:
    del runtime_data_dir
    events = query_events(kol_query="KOL_A", event_type="move_to_breakeven")
    assert events[0].event_type == "move_to_breakeven"


def test_query_opinions(runtime_data_dir: object) -> None:
    del runtime_data_dir
    opinions = query_opinions(kol_query="KOL_A", symbol="ETH")
    assert opinions[0].symbol == "ETH"


def test_query_news(runtime_data_dir: object) -> None:
    del runtime_data_dir
    news = query_news(symbol="SOL")
    assert news


def test_kol_not_found_handled(runtime_data_dir: object) -> None:
    del runtime_data_dir
    with pytest.raises(DomainError):
        search_evidence(kol_query="KOL_Z")
