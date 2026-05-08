from __future__ import annotations

import pytest

from crypto_helper.core.hybrid_retriever import (
    _collect_structured_candidates,
    hybrid_search_evidence,
)
from crypto_helper.models.vector import VectorSearchResult


def test_query_uses_hybrid_when_vector_available(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")
    candidates = _collect_structured_candidates(
        kol_query="KOL_A",
        symbol="BTC",
        source_type=None,
        time_range=None,
    )
    target = candidates[0]

    def fake_search(
        self: object,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        del self, query, top_k, filters
        return [
            VectorSearchResult(
                doc_id=f"doc:{target.evidence_id}",
                evidence_id=target.evidence_id,
                score=0.99,
                kol_id=target.kol_id,
                symbol=target.symbol,
                source_type=target.source_type,
                summary=target.summary,
            )
        ]

    monkeypatch.setattr("crypto_helper.core.hybrid_retriever.VectorStore.search", fake_search)

    result = hybrid_search_evidence(
        kol_query="KOL_A",
        symbol="BTC",
        query="invalidation reclaim",
        limit=3,
    )

    assert result.items
    assert result.items[0].evidence_id == target.evidence_id


def test_kol_filter_is_respected_in_hybrid_results(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")

    def fake_search(
        self: object,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        del self, query, top_k
        return [
            VectorSearchResult(
                doc_id="doc:foreign",
                evidence_id="foreign",
                score=0.99,
                kol_id="kol_b",
                symbol="BTC",
                source_type="opinion",
                summary="foreign result",
            )
        ]

    monkeypatch.setattr("crypto_helper.core.hybrid_retriever.VectorStore.search", fake_search)

    result = hybrid_search_evidence(
        kol_query="KOL_A",
        query="btc view",
        limit=5,
    )

    assert result.items
    assert all(item.kol_id == "kol_a" for item in result.items if item.kol_id is not None)


def test_symbol_filter_is_respected_in_hybrid_results(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")

    def fake_search(
        self: object,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        del self, query, top_k, filters
        return []

    monkeypatch.setattr("crypto_helper.core.hybrid_retriever.VectorStore.search", fake_search)

    result = hybrid_search_evidence(
        symbol="SOL",
        query="market risk",
        limit=5,
    )

    assert result.items
    assert all(item.symbol == "SOL" for item in result.items if item.symbol is not None)


def test_vector_failure_falls_back_to_structured(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: object,
) -> None:
    del runtime_data_dir
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")

    def failing_search(
        self: object,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        del self, query, top_k, filters
        raise RuntimeError("vector unavailable")

    monkeypatch.setattr("crypto_helper.core.hybrid_retriever.VectorStore.search", failing_search)

    result = hybrid_search_evidence(
        kol_query="KOL_A",
        symbol="BTC",
        query="invalidation",
        limit=5,
    )

    assert result.items
    assert any("fallback" in limitation.lower() for limitation in result.limitations)
