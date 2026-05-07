from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from crypto_helper.core.data_loader import append_jsonl, load_json, save_json, save_yaml
from crypto_helper.models.common import DomainError
from crypto_helper.models.persona import KOLProfile
from crypto_helper.models.registry import (
    KOLRegistry,
    KOLRegistryEntry,
    KOLStatus,
    KOLTier,
    PersonaMode,
)
from crypto_helper.models.soul import (
    IdentityBoundary,
    KOLSoul,
    LanguageSoul,
    ReasoningStyle,
    SafetyRules,
    TradingSoul,
    UpdatePolicy,
)


def list_kols(status: str = "active") -> list[KOLRegistryEntry]:
    registry = _load_registry()
    if status == "all":
        return registry.kols
    try:
        target_status = KOLStatus(status)
    except ValueError as exc:
        raise DomainError(f"Unsupported status: {status}", code="INVALID_STATUS") from exc
    return [entry for entry in registry.kols if entry.status == target_status]


def lookup_kol(query: str) -> KOLRegistryEntry | None:
    normalized = _normalize_lookup_value(query)
    for entry in _load_registry().kols:
        candidates = [entry.kol_id, entry.display_name, *entry.aliases]
        if normalized in {_normalize_lookup_value(candidate) for candidate in candidates}:
            return entry
    return None


def get_active_kols() -> list[KOLRegistryEntry]:
    return list_kols(status=KOLStatus.ACTIVE.value)


def require_kol(query: str) -> KOLRegistryEntry:
    entry = lookup_kol(query)
    if entry is None:
        raise DomainError(
            f"KOL not found: {query}", code="KOL_NOT_FOUND", metadata={"query": query}
        )
    return entry


def add_mock_kol(
    display_name: str, aliases: list[str], allowed_symbols: list[str]
) -> dict[str, Any]:
    registry = _load_registry()
    kol_id = _slugify(display_name)
    if lookup_kol(display_name) or lookup_kol(kol_id):
        raise DomainError(
            f"KOL already exists: {display_name}",
            code="KOL_ALREADY_EXISTS",
            metadata={"display_name": display_name},
        )
    timestamp = _now()
    symbols = sorted({symbol.strip().upper() for symbol in allowed_symbols if symbol.strip()})
    entry = KOLRegistryEntry(
        kol_id=kol_id,
        display_name=display_name,
        aliases=aliases,
        status=KOLStatus.ACTIVE,
        tier=KOLTier.DYNAMIC,
        persona_mode=PersonaMode.RUNTIME_ONLY,
        soul_path=f"kols/{kol_id}/soul.yaml",
        profile_path=f"kols/{kol_id}/profile.json",
        evidence_path=f"kols/{kol_id}/evidence.json",
        allowed_symbols=symbols,
        risk_level="unknown",
        last_updated=timestamp,
    )
    registry.kols.append(entry)
    registry.kols.sort(key=lambda item: item.kol_id)
    save_json("registry/kols.json", registry.model_dump(mode="json"))
    _write_default_kol_files(entry)
    audit_path = append_jsonl(
        "audit/registry_changes.jsonl",
        {
            "timestamp": timestamp,
            "action": "add_mock",
            "kol_id": entry.kol_id,
            "display_name": entry.display_name,
            "mock_only": True,
            "allowed_symbols": symbols,
        },
    )
    return {"entry": entry, "mock_only": True, "audit_path": str(audit_path)}


def disable_kol(kol_query: str) -> dict[str, Any]:
    return _update_status(kol_query, KOLStatus.DISABLED, "disable_mock")


def archive_kol(kol_query: str) -> dict[str, Any]:
    return _update_status(kol_query, KOLStatus.ARCHIVED, "archive_mock")


def _update_status(kol_query: str, target: KOLStatus, action: str) -> dict[str, Any]:
    registry = _load_registry()
    updated: KOLRegistryEntry | None = None
    for index, entry in enumerate(registry.kols):
        if lookup_kol(kol_query) and entry.kol_id == require_kol(kol_query).kol_id:
            updated = entry.model_copy(update={"status": target, "last_updated": _now()})
            registry.kols[index] = updated
            break
    if updated is None:
        raise DomainError(f"KOL not found: {kol_query}", code="KOL_NOT_FOUND")
    save_json("registry/kols.json", registry.model_dump(mode="json"))
    audit_path = append_jsonl(
        "audit/registry_changes.jsonl",
        {
            "timestamp": _now(),
            "action": action,
            "kol_id": updated.kol_id,
            "status": updated.status,
            "mock_only": True,
        },
    )
    return {"entry": updated, "mock_only": True, "audit_path": str(audit_path)}


def _load_registry() -> KOLRegistry:
    raw = load_json("registry/kols.json")
    return KOLRegistry.model_validate(raw)


def _write_default_kol_files(entry: KOLRegistryEntry) -> None:
    soul = KOLSoul(
        kol_id=entry.kol_id,
        identity_boundary=IdentityBoundary(
            must_not_claim_real_identity=True,
            must_state_simulation=True,
        ),
        trading_soul=TradingSoul(
            style_traits=["sparse_evidence", "runtime_only"],
            preferred_setups=["wait_for_more_evidence"],
            risk_management=["small_size"],
        ),
        reasoning_style=ReasoningStyle(
            summary="Uses weak-evidence simulation and keeps conclusions conditional.",
            key_patterns=["state uncertainty", "prefer historical references"],
        ),
        language_soul=LanguageSoul(
            tone="cautious",
            disclaimers=["这是基于历史画像的模拟推理，不代表该 KOL 本人实时观点。"],
        ),
        safety_rules=SafetyRules(
            no_direct_financial_advice=True,
            must_include_evidence=True,
            must_include_confidence=True,
            must_include_limitations=True,
        ),
        update_policy=UpdatePolicy(),
    )
    profile = KOLProfile(
        kol_id=entry.kol_id,
        summary=f"{entry.display_name} is a dynamic mock KOL with limited history.",
        active_symbols=entry.allowed_symbols,
        trade_style=["low_evidence_runtime_profile"],
        reliability=0.42,
        evidence_strength=0,
        last_refreshed=_now(),
        limitations=["Fresh dynamic KOL with sparse mock evidence."],
    )
    save_yaml(entry.soul_path, soul.model_dump(mode="json"))
    save_json(entry.profile_path, profile.model_dump(mode="json"))
    save_json(entry.evidence_path, {"items": []})


def _normalize_lookup_value(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value).lower()


def _slugify(display_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", display_name.strip()).strip("_").lower()
    if not normalized.startswith("kol_"):
        normalized = f"kol_{normalized}"
    return normalized


def _now() -> datetime:
    return datetime.now(UTC)
