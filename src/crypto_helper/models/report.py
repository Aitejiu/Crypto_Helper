from __future__ import annotations

from typing import Any

from pydantic import Field

from crypto_helper.evidence.schemas import EvidenceBackedClaim
from crypto_helper.models.common import DomainModel
from crypto_helper.models.evidence import EvidenceRef


class ReportResult(DomainModel):
    title: str
    markdown: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    claims: list[EvidenceBackedClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
