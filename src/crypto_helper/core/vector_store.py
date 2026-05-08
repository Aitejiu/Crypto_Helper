from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from crypto_helper.core.data_loader import load_json
from crypto_helper.core.paths import get_vector_index_dir
from crypto_helper.core.vector_config import (
    get_embedding_model,
    get_vector_backend,
    is_vector_enabled,
)
from crypto_helper.models.common import to_jsonable
from crypto_helper.models.evidence import EvidenceRef, KOLOpinion, MarketNews
from crypto_helper.models.registry import KOLRegistry, KOLRegistryEntry
from crypto_helper.models.vector import VectorDocument, VectorIndexStatus, VectorSearchResult

COLLECTION_NAME = "crypto_helper_vector_documents"
MANIFEST_NAME = "manifest.json"


class VectorStore:
    def __init__(self) -> None:
        self.enabled = is_vector_enabled()
        self.backend = get_vector_backend()
        self.embedding_model = get_embedding_model()
        self.index_dir = get_vector_index_dir() / self.backend
        self._client: Any | None = None
        self._collection: Any | None = None
        self._embedding_model: Any | None = None

    def rebuild_index(self) -> VectorIndexStatus:
        if not self.enabled:
            return self.status()
        documents = build_vector_documents()
        client = self._get_client()
        collection = self._reset_collection(client)
        if documents:
            texts = [document.text for document in documents]
            embeddings = self._embed_texts(texts)
            collection.add(
                ids=[document.doc_id for document in documents],
                documents=texts,
                embeddings=embeddings,
                metadatas=[_metadata_for_storage(document) for document in documents],
            )
        manifest = {
            "document_count": len(documents),
            "last_updated": _now().isoformat(),
            "embedding_model": self.embedding_model,
            "backend": self.backend,
            "enabled": True,
        }
        self.index_dir.mkdir(parents=True, exist_ok=True)
        _write_json(self.index_dir / MANIFEST_NAME, manifest)
        self._collection = collection
        return self.status()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if not self.enabled:
            return []
        collection = self._get_collection()
        query_embedding = self._embed_texts([query])[0]
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=_normalize_filters(filters),
        )
        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            _search_result_from_storage(
                doc_id=doc_id,
                metadata=metadata or {},
                distance=distance,
            )
            for doc_id, metadata, distance in zip(ids, metadatas, distances, strict=False)
        ]

    def status(self) -> VectorIndexStatus:
        if not self.enabled:
            return VectorIndexStatus(
                index_path=str(self.index_dir),
                document_count=0,
                last_updated=None,
                embedding_model=self.embedding_model,
                backend=self.backend,
                enabled=False,
            )
        manifest_path = self.index_dir / MANIFEST_NAME
        if manifest_path.exists():
            payload = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
            return VectorIndexStatus(
                index_path=str(self.index_dir),
                document_count=int(payload.get("document_count", 0)),
                last_updated=_parse_optional_timestamp(payload.get("last_updated")),
                embedding_model=str(payload.get("embedding_model", self.embedding_model)),
                backend=str(payload.get("backend", self.backend)),
                enabled=bool(payload.get("enabled", True)),
            )
        return VectorIndexStatus(
            index_path=str(self.index_dir),
            document_count=0,
            last_updated=None,
            embedding_model=self.embedding_model,
            backend=self.backend,
            enabled=True,
        )

    def clear(self) -> VectorIndexStatus:
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir)
        self._client = None
        self._collection = None
        return self.status()

    def _get_client(self) -> Any:
        if self._client is None:
            import chromadb

            self.index_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.index_dir))
        return self._client

    def _get_collection(self) -> Any:
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(name=COLLECTION_NAME)
        return self._collection

    def _reset_collection(self, client: Any) -> Any:
        with suppress(Exception):
            client.delete_collection(COLLECTION_NAME)
        return client.get_or_create_collection(name=COLLECTION_NAME)

    def _get_embedding_model(self) -> Any:
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self.embedding_model)
        return self._embedding_model

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, embedding)) for embedding in embeddings]


def build_vector_documents() -> list[VectorDocument]:
    registry = _load_registry()
    display_names = {entry.kol_id: entry.display_name for entry in registry.kols}
    documents: list[VectorDocument] = []
    documents.extend(_build_evidence_documents(registry.kols, display_names))
    documents.extend(_build_opinion_documents(display_names))
    documents.extend(_build_news_documents())
    documents.sort(key=lambda document: (document.timestamp, document.doc_id), reverse=True)
    return documents


def build_vector_documents_for_kol(kol_id: str) -> list[VectorDocument]:
    return [document for document in build_vector_documents() if document.kol_id == kol_id]


def _load_registry() -> KOLRegistry:
    raw = load_json("registry/kols.json")
    return KOLRegistry.model_validate(raw)


def _build_evidence_documents(
    entries: Iterable[KOLRegistryEntry],
    display_names: dict[str, str],
) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    for entry in entries:
        raw = load_json(entry.evidence_path)
        for item in raw.get("items", []):
            evidence = EvidenceRef.model_validate(item)
            documents.append(
                VectorDocument(
                    doc_id=f"evidence:{evidence.evidence_id}",
                    evidence_id=evidence.evidence_id,
                    kol_id=evidence.kol_id,
                    display_name=display_names.get(evidence.kol_id or ""),
                    symbol=evidence.symbol,
                    source_type=evidence.source_type,
                    timestamp=evidence.timestamp,
                    channel_scope=evidence.channel_scope,
                    confidence=evidence.confidence,
                    text=_format_embedding_text(
                        display_name=display_names.get(evidence.kol_id or ""),
                        symbol=evidence.symbol,
                        source_type=evidence.source_type,
                        summary=evidence.summary,
                        confidence=evidence.confidence,
                        timestamp=evidence.timestamp.isoformat(),
                    ),
                    metadata={
                        "source_path": entry.evidence_path,
                        "source_id": evidence.source_id,
                    },
                )
            )
    return documents


def _build_opinion_documents(display_names: dict[str, str]) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    for item in load_json("mock/opinions.json"):
        opinion = KOLOpinion.model_validate(item)
        display_name = display_names.get(opinion.kol_id)
        source_kind = (
            "market_analysis"
            if opinion.evidence_id.startswith("import_market_analysis_")
            else "opinion"
        )
        documents.append(
            VectorDocument(
                doc_id=f"opinion:{opinion.evidence_id}",
                evidence_id=opinion.evidence_id,
                kol_id=opinion.kol_id,
                display_name=display_name,
                symbol=opinion.symbol,
                source_type=source_kind,
                timestamp=opinion.timestamp,
                channel_scope=opinion.channel_scope,
                confidence=opinion.confidence,
                text=_format_embedding_text(
                    display_name=display_name,
                    symbol=opinion.symbol,
                    source_type=source_kind,
                    summary=opinion.summary,
                    confidence=opinion.confidence,
                    timestamp=opinion.timestamp.isoformat(),
                ),
                metadata={
                    "source_path": "mock/opinions.json",
                    "source_id": opinion.id,
                    "sentiment": opinion.sentiment,
                },
            )
        )
    return documents


def _build_news_documents() -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    for item in load_json("mock/news.json"):
        news = MarketNews.model_validate(item)
        documents.append(
            VectorDocument(
                doc_id=f"news:{news.evidence_id}",
                evidence_id=news.evidence_id,
                kol_id=None,
                display_name=None,
                symbol=news.symbol,
                source_type="news",
                timestamp=news.timestamp,
                channel_scope=news.channel_scope,
                confidence=news.confidence,
                text=_format_embedding_text(
                    display_name=None,
                    symbol=news.symbol,
                    source_type="news",
                    summary=news.summary,
                    confidence=news.confidence,
                    timestamp=news.timestamp.isoformat(),
                ),
                metadata={
                    "source_path": "mock/news.json",
                    "source_id": news.id,
                    "importance": news.importance,
                },
            )
        )
    return documents


def _format_embedding_text(
    *,
    display_name: str | None,
    symbol: str | None,
    source_type: str,
    summary: str,
    confidence: float,
    timestamp: str,
) -> str:
    return "\n".join(
        [
            f"KOL: {display_name or 'N/A'}",
            f"Symbol: {symbol or 'N/A'}",
            f"Source Type: {source_type}",
            f"Summary: {summary}",
            f"Confidence: {confidence:.2f}",
            f"Timestamp: {timestamp}",
        ]
    )


def _metadata_for_storage(document: VectorDocument) -> dict[str, str | float | int | bool]:
    metadata: dict[str, str | float | int | bool] = {
        "evidence_id": document.evidence_id,
        "source_type": document.source_type,
        "timestamp": document.timestamp.isoformat(),
        "channel_scope": document.channel_scope,
        "confidence": document.confidence,
    }
    if document.kol_id is not None:
        metadata["kol_id"] = document.kol_id
    if document.display_name is not None:
        metadata["display_name"] = document.display_name
    if document.symbol is not None:
        metadata["symbol"] = document.symbol
    for key, value in document.metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, float, int, bool)):
            metadata[key] = value
        else:
            metadata[key] = json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return metadata


def _search_result_from_storage(
    *,
    doc_id: str,
    metadata: dict[str, Any],
    distance: float,
) -> VectorSearchResult:
    return VectorSearchResult(
        doc_id=doc_id,
        evidence_id=str(metadata["evidence_id"]),
        score=max(0.0, 1.0 - float(distance)),
        kol_id=_string_or_none(metadata.get("kol_id")),
        display_name=_string_or_none(metadata.get("display_name")),
        symbol=_string_or_none(metadata.get("symbol")),
        source_type=str(metadata["source_type"]),
        summary=_string_or_none(metadata.get("summary")),
        metadata={
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "evidence_id",
                "kol_id",
                "display_name",
                "symbol",
                "source_type",
                "summary",
            }
        },
    )


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    if not filters:
        return None
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if value is None:
            continue
        normalized[key] = value
    return normalized or None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(payload), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _parse_optional_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _now() -> datetime:
    return datetime.now(UTC)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
