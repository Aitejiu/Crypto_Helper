from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from crypto_helper.models.common import DomainModel


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceRef(DomainModel):
    type: str
    id: str
    timestamp: datetime
    source: str
    kol_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBackedClaim(DomainModel):
    claim: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: ConfidenceLevel
    unsupported_reason: str | None = None


class EvidenceContract(DomainModel):
    claims: list[EvidenceBackedClaim] = Field(default_factory=list)
