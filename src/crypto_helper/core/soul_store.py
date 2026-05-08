from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from crypto_helper.core.data_loader import append_jsonl, load_jsonl, load_yaml, save_yaml
from crypto_helper.core.profile_service import get_profile as get_profile_payload
from crypto_helper.core.registry_service import require_kol
from crypto_helper.models.common import DomainError
from crypto_helper.models.registry import KOLStatus
from crypto_helper.models.soul import KOLSoul, SoulPatch
from crypto_helper.services.audit_service import write_profile_audit


def get_soul(kol_query: str) -> dict[str, Any]:
    entry = require_kol(kol_query)
    soul = KOLSoul.model_validate(load_yaml(entry.soul_path))
    limitations: list[str] = []
    if entry.status == KOLStatus.DISABLED:
        limitations.append("Disabled KOL soul is available for audit only.")
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append("Archived KOL soul is available for historical analysis only.")
    return {"soul": soul, "limitations": limitations}


def get_profile(kol_query: str) -> dict[str, Any]:
    return get_profile_payload(kol_query)


def generate_soul_patch_mock(kol_query: str, observed_behavior: str) -> dict[str, Any]:
    entry = require_kol(kol_query)
    if entry.status == KOLStatus.DISABLED:
        raise DomainError(
            "Disabled KOL does not allow persona-oriented soul patch generation.",
            code="KOL_DISABLED",
        )
    lowered = observed_behavior.lower()
    additions: list[str] = []
    reasoning_additions: list[str] = []
    confidence = 0.42
    if "breakeven" in lowered:
        additions.append("move_sl_to_breakeven")
        reasoning_additions.append("protect risk once partial TP is available")
        confidence = 0.74
    if "invalidation" in lowered:
        additions.append("restate_invalidation_before_entry")
        reasoning_additions.append("anchor invalidation before scenario conclusion")
        confidence = max(confidence, 0.72)
    if "reclaim" in lowered:
        additions.append("prefer_reclaim_confirmation")
        reasoning_additions.append("wait for reclaim before confidence upgrade")
        confidence = max(confidence, 0.7)
    if not additions:
        additions.append("observe_more_behavior")
        reasoning_additions.append("evidence remains sparse")
    patch = SoulPatch(
        patch_id=f"patch_{uuid.uuid4().hex[:10]}",
        kol_id=entry.kol_id,
        observed_behavior=observed_behavior,
        summary=f"Mock patch generated from observed behavior: {observed_behavior}",
        confidence=round(confidence, 2),
        requires_review=confidence < 0.6,
        trading_style_additions=additions,
        reasoning_pattern_additions=reasoning_additions,
        identity_boundary_updates=None,
        metadata={"mock_only": True},
        created_at=_now(),
    )
    audit_path = append_jsonl(
        "audit/soul_patches.jsonl",
        {
            "event": "generated",
            "timestamp": _now(),
            "kol_id": entry.kol_id,
            "patch": patch.model_dump(mode="json"),
            "mock_only": True,
        },
    )
    write_profile_audit(
        event_type="soul_patch_generated",
        actor="system",
        target_type="kol_soul",
        target_id=entry.kol_id,
        action="generate_soul_patch_mock",
        after=patch.model_dump(mode="json"),
        status="success",
    )
    return {"patch": patch, "audit_path": str(audit_path), "mock_only": True}


def apply_soul_patch_mock(kol_query: str, patch_id: str | None = None) -> dict[str, Any]:
    entry = require_kol(kol_query)
    soul = KOLSoul.model_validate(load_yaml(entry.soul_path))
    patch = _select_patch(entry.kol_id, patch_id)
    if patch.identity_boundary_updates and (
        patch.identity_boundary_updates.get("must_not_claim_real_identity") is False
    ):
        raise DomainError(
            "Soul patches cannot disable real identity protection.",
            code="INVALID_SOUL_PATCH",
        )
    if patch.requires_review and patch_id is None:
        raise DomainError(
            "Low-confidence patch requires explicit review via patch_id.",
            code="PATCH_REQUIRES_REVIEW",
        )
    for addition in patch.trading_style_additions:
        if addition not in soul.trading_soul.style_traits:
            soul.trading_soul.style_traits.append(addition)
    for addition in patch.reasoning_pattern_additions:
        if addition not in soul.reasoning_style.key_patterns:
            soul.reasoning_style.key_patterns.append(addition)
    if patch.identity_boundary_updates:
        for key, value in patch.identity_boundary_updates.items():
            setattr(soul.identity_boundary, key, value)
    save_yaml(entry.soul_path, soul.model_dump(mode="json"))
    audit_path = append_jsonl(
        "audit/soul_patches.jsonl",
        {
            "event": "applied",
            "timestamp": _now(),
            "kol_id": entry.kol_id,
            "patch_id": patch.patch_id,
            "mock_only": True,
        },
    )
    write_profile_audit(
        event_type="soul_patch_applied",
        actor="system",
        target_type="kol_soul",
        target_id=entry.kol_id,
        action="apply_soul_patch_mock",
        after={"patch_id": patch.patch_id},
        status="success",
    )
    limitations: list[str] = []
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append("Applied on archived KOL history only.")
    return {
        "soul": soul,
        "patch": patch,
        "limitations": limitations,
        "audit_path": str(audit_path),
        "mock_only": True,
    }


def _select_patch(kol_id: str, patch_id: str | None) -> SoulPatch:
    rows = load_jsonl("audit/soul_patches.jsonl")
    generated: list[SoulPatch] = []
    applied_ids: set[str] = set()
    for row in rows:
        if row.get("event") == "generated" and row.get("kol_id") == kol_id:
            generated.append(SoulPatch.model_validate(row["patch"]))
        if row.get("event") == "applied":
            current_patch_id = row.get("patch_id")
            if isinstance(current_patch_id, str):
                applied_ids.add(current_patch_id)
    if patch_id:
        for patch in generated:
            if patch.patch_id == patch_id:
                return patch
        raise DomainError(f"Patch not found: {patch_id}", code="PATCH_NOT_FOUND")
    unapplied = [patch for patch in generated if patch.patch_id not in applied_ids]
    if not unapplied:
        raise DomainError("No pending soul patch found.", code="PATCH_NOT_FOUND")
    return sorted(unapplied, key=lambda patch: patch.created_at, reverse=True)[0]


def _now() -> datetime:
    return datetime.now(UTC)
