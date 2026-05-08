from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from crypto_helper.evidence.schemas import EvidenceBackedClaim
from crypto_helper.models.common import DomainModel
from crypto_helper.models.evidence import EvidenceRef


class KOLProfile(DomainModel):
    kol_id: str
    summary: str
    active_symbols: list[str] = Field(default_factory=list)
    trade_style: list[str] = Field(default_factory=list)
    reliability: float
    evidence_strength: int
    last_refreshed: datetime
    limitations: list[str] = Field(default_factory=list)


class PersonaAnswer(DomainModel):
    disclaimer: str
    answer: str
    reasoning: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    claims: list[EvidenceBackedClaim] = Field(default_factory=list)
    confidence: float
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("disclaimer is required")
        return value
