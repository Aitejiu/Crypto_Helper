from __future__ import annotations

from typing import Any

from crypto_helper.evidence.schemas import EvidenceBackedClaim


def validate_claims_against_evidence(
    claims: list[EvidenceBackedClaim],
    evidence_store: Any,
) -> tuple[list[EvidenceBackedClaim], list[dict[str, str]]]:
    validated: list[EvidenceBackedClaim] = []
    issues: list[dict[str, str]] = []
    for claim in claims:
        if not claim.evidence_refs:
            validated.append(
                claim.model_copy(update={"unsupported_reason": "No evidence references provided."})
            )
            issues.append(
                {
                    "code": "unsupported_claim",
                    "claim": claim.claim,
                }
            )
            continue
        invalid_refs = [
            reference.id
            for reference in claim.evidence_refs
            if not _evidence_exists(evidence_store, reference.id)
        ]
        if invalid_refs:
            validated.append(
                claim.model_copy(
                    update={
                        "unsupported_reason": (
                            "Missing evidence references: " + ", ".join(invalid_refs)
                        )
                    }
                )
            )
            for ref_id in invalid_refs:
                issues.append(
                    {
                        "code": "invalid_evidence_ref",
                        "claim": claim.claim,
                        "evidence_id": ref_id,
                    }
                )
            continue
        validated.append(claim)
    return validated, issues


def _evidence_exists(evidence_store: Any, evidence_id: str) -> bool:
    if callable(evidence_store):
        lookup = evidence_store(evidence_id)
        return bool(lookup)
    if isinstance(evidence_store, dict):
        return evidence_id in evidence_store
    if isinstance(evidence_store, set):
        return evidence_id in evidence_store
    return False
