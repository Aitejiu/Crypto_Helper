from __future__ import annotations

from crypto_helper.evidence.schemas import (
    ConfidenceLevel,
    EvidenceBackedClaim,
    EvidenceContract,
    EvidenceRef,
)


def build_claim(
    claim: str,
    *,
    evidence_refs: list[EvidenceRef] | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    unsupported_reason: str | None = None,
) -> EvidenceBackedClaim:
    return EvidenceBackedClaim(
        claim=claim,
        evidence_refs=evidence_refs or [],
        confidence=confidence,
        unsupported_reason=unsupported_reason,
    )


def build_contract(claims: list[EvidenceBackedClaim]) -> EvidenceContract:
    return EvidenceContract(claims=claims)
