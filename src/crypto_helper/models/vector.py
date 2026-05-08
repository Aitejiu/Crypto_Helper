from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel


class VectorDocument(DomainModel):
    doc_id: str
    evidence_id: str
    kol_id: str | None = None
    display_name: str | None = None
    symbol: str | None = None
    source_type: str
    timestamp: datetime
    channel_scope: str
    confidence: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResult(DomainModel):
    doc_id: str
    evidence_id: str
    score: float
    kol_id: str | None = None
    display_name: str | None = None
    symbol: str | None = None
    source_type: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorIndexStatus(DomainModel):
    index_path: str
    document_count: int
    last_updated: datetime | None = None
    embedding_model: str
    backend: str
    enabled: bool
