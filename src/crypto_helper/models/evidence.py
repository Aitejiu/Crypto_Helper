from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel


class EvidenceRef(DomainModel):
    evidence_id: str
    source_type: str
    source_id: str
    kol_id: str | None = None
    symbol: str | None = None
    timestamp: datetime
    channel_scope: str
    summary: str
    confidence: float


class EvidenceSearchResult(DomainModel):
    items: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    query: dict[str, Any] = Field(default_factory=dict)
    total: int = 0


class TradeCall(DomainModel):
    id: str
    evidence_id: str
    kol_id: str
    symbol: str
    side: str
    thesis: str
    status: str
    entry_zone: str
    invalidation: str
    timestamp: datetime
    channel_scope: str
    summary: str
    confidence: float
    outcome_score: float | None = None


class TradeCallEvent(DomainModel):
    id: str
    evidence_id: str
    trade_call_id: str
    kol_id: str
    symbol: str
    event_type: str
    timestamp: datetime
    channel_scope: str
    summary: str
    confidence: float


class KOLOpinion(DomainModel):
    id: str
    evidence_id: str
    kol_id: str
    symbol: str
    sentiment: str
    timestamp: datetime
    channel_scope: str
    summary: str
    confidence: float


class MarketNews(DomainModel):
    id: str
    evidence_id: str
    symbol: str
    importance: str
    timestamp: datetime
    channel_scope: str
    summary: str
    confidence: float
