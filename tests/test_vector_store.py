from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from crypto_helper.core import paths
from crypto_helper.core.data_loader import load_json, save_json_path
from crypto_helper.core.vector_store import VectorStore, build_vector_documents


def test_market_analysis_records_enter_vector_documents(runtime_data_dir: object) -> None:
    del runtime_data_dir
    data_dir = paths.ensure_runtime_data()
    opinions_path = data_dir / "mock" / "opinions.json"
    opinions = load_json("mock/opinions.json")
    opinions.append(
        {
            "id": "analysis-1",
            "evidence_id": "import_market_analysis_analysis-1",
            "kol_id": "kol_a",
            "symbol": "BTC",
            "sentiment": "bullish",
            "timestamp": datetime(2026, 5, 8, 12, 0, tzinfo=UTC).isoformat(),
            "channel_scope": "imported_channel:test",
            "summary": "BTC reclaim analysis with invalidation and continuation framing.",
            "confidence": 0.77,
        }
    )
    save_json_path(opinions_path, opinions)
    documents = build_vector_documents()

    assert any(document.source_type == "market_analysis" for document in documents)


def test_news_records_enter_vector_documents(runtime_data_dir: object) -> None:
    del runtime_data_dir
    documents = build_vector_documents()

    assert any(document.source_type == "news" for document in documents)


def test_raw_private_messages_are_not_indexed(runtime_data_dir: Path) -> None:
    data_dir = paths.ensure_runtime_data()
    raw_messages_path = data_dir / "discord_messages.json"
    raw_messages_path.write_text(
        json.dumps(
            [
                {
                    "message_id": "private-1",
                    "content": "raw private message that must never be indexed",
                }
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    documents = build_vector_documents()

    assert not any(
        "raw private message that must never be indexed" in document.text for document in documents
    )


def test_rebuild_index_succeeds(monkeypatch: pytest.MonkeyPatch, runtime_data_dir: Path) -> None:
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")
    store = VectorStore()
    monkeypatch.setattr(store, "_embed_texts", _fake_embeddings.__get__(store, VectorStore))

    status = store.rebuild_index()

    assert status.enabled is True
    assert status.backend == "chroma"
    assert status.document_count > 0
    assert (runtime_data_dir / "vector_index" / "chroma" / "manifest.json").exists()


def test_status_returns_index_info(monkeypatch: pytest.MonkeyPatch, runtime_data_dir: Path) -> None:
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")
    store = VectorStore()
    monkeypatch.setattr(store, "_embed_texts", _fake_embeddings.__get__(store, VectorStore))
    store.rebuild_index()

    status = store.status()

    assert status.index_path.endswith("vector_index/chroma")
    assert status.embedding_model == "BAAI/bge-m3"
    assert status.document_count > 0


def test_search_returns_structured_results(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: Path,
) -> None:
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "true")
    store = VectorStore()
    monkeypatch.setattr(store, "_embed_texts", _fake_embeddings.__get__(store, VectorStore))
    store.rebuild_index()

    results = store.search("SOL market update", top_k=5)

    assert results
    assert all(result.doc_id for result in results)
    assert any(result.source_type == "news" for result in results)


def test_disabled_mode_returns_disabled_status(
    monkeypatch: pytest.MonkeyPatch,
    runtime_data_dir: Path,
) -> None:
    del runtime_data_dir
    monkeypatch.setenv("CRYPTO_HELPER_VECTOR_ENABLED", "false")
    store = VectorStore()

    status = store.status()

    assert status.enabled is False
    assert status.document_count == 0
    assert store.search("anything") == []


def _fake_embeddings(self: VectorStore, texts: list[str]) -> list[list[float]]:
    del self
    embeddings: list[list[float]] = []
    for text in texts:
        lowered = text.lower()
        embeddings.append(
            [
                1.0 if "sol" in lowered else 0.0,
                1.0 if "btc" in lowered else 0.0,
                1.0 if "market" in lowered else 0.0,
                1.0 if "news" in lowered else 0.0,
                max(len(text), 1) / 1000.0,
            ]
        )
    return embeddings
