from __future__ import annotations

from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel
from crypto_helper.models.evidence import EvidenceRef


class KOLRankingItem(DomainModel):
    kol_id: str
    display_name: str
    score: float
    sample_size: int
    metrics: dict[str, float] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float


class KOLPerformance(DomainModel):
    kol_id: str
    display_name: str
    sample_size: int
    metrics: dict[str, float] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float


class StatsResult(DomainModel):
    title: str
    sample_size: int
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    rankings: list[KOLRankingItem] = Field(default_factory=list)
    performance: KOLPerformance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
