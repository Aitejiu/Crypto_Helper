from __future__ import annotations

from datetime import UTC, datetime

from crypto_helper.evidence import ConfidenceLevel
from crypto_helper.evidence.schemas import EvidenceBackedClaim, EvidenceRef
from crypto_helper.evidence.validator import validate_claims_against_evidence


def test_claim_with_valid_evidence_refs() -> None:
    claim = EvidenceBackedClaim(
        claim="BTC reclaim was discussed repeatedly.",
        evidence_refs=[
            EvidenceRef(
                type="opinion",
                id="evidence-1",
                timestamp=datetime.now(UTC),
                source="mock/opinions.json",
            )
        ],
        confidence=ConfidenceLevel.MEDIUM,
    )

    validated, issues = validate_claims_against_evidence(
        claims=[claim], evidence_store={"evidence-1": {}}
    )

    assert validated[0].unsupported_reason is None
    assert issues == []


def test_claim_without_evidence_refs_is_unsupported() -> None:
    claim = EvidenceBackedClaim(
        claim="Unbacked claim",
        evidence_refs=[],
        confidence=ConfidenceLevel.LOW,
    )

    validated, issues = validate_claims_against_evidence(claims=[claim], evidence_store={})

    assert validated[0].unsupported_reason == "No evidence references provided."
    assert issues[0]["code"] == "unsupported_claim"


def test_claim_with_missing_evidence_ref_is_invalid() -> None:
    claim = EvidenceBackedClaim(
        claim="Missing evidence claim",
        evidence_refs=[
            EvidenceRef(
                type="report",
                id="missing-evidence",
                timestamp=datetime.now(UTC),
                source="reports/test.json",
            )
        ],
        confidence=ConfidenceLevel.HIGH,
    )

    validated, issues = validate_claims_against_evidence(claims=[claim], evidence_store={})

    assert validated[0].unsupported_reason == "Missing evidence references: missing-evidence"
    assert issues[0]["code"] == "invalid_evidence_ref"
