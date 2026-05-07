from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
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


@dataclass(frozen=True)
class KOLLookupMatch:
    entry: KOLRegistryEntry
    score: float
    matched_by: str
    matched_value: str


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
    exact = _exact_lookup(query)
    if exact is not None:
        return exact
    entry = resolve_kol_query(query).get("entry")
    return entry if isinstance(entry, KOLRegistryEntry) else None


def resolve_kol_query(query: str, *, suggestion_limit: int = 5) -> dict[str, Any]:
    registry = _load_registry()
    matches = _rank_kol_matches(registry.kols, query)
    suggestions = _suggestion_payload(matches, suggestion_limit)
    if not matches:
        return {
            "query": query,
            "entry": None,
            "matched_by": None,
            "matched_value": None,
            "confidence": 0.0,
            "ambiguous": False,
            "suggestions": suggestions,
            "hint": "查看 KOL 列表，确认具体名字。",
            "list_command": "crypto-helper registry list --json",
        }

    best = matches[0]
    auto_match = _should_auto_match(query, matches)
    if auto_match:
        return {
            "query": query,
            "entry": best.entry,
            "matched_by": best.matched_by,
            "matched_value": best.matched_value,
            "confidence": round(best.score, 3),
            "ambiguous": False,
            "suggestions": suggestions,
            "hint": None,
            "list_command": None,
        }

    return {
        "query": query,
        "entry": None,
        "matched_by": None,
        "matched_value": None,
        "confidence": round(best.score, 3),
        "ambiguous": True,
        "suggestions": suggestions,
        "hint": "查看 KOL 列表，确认具体名字。",
        "list_command": "crypto-helper registry list --json",
    }


def get_active_kols() -> list[KOLRegistryEntry]:
    return list_kols(status=KOLStatus.ACTIVE.value)


def require_kol(query: str) -> KOLRegistryEntry:
    resolution = resolve_kol_query(query)
    entry = resolution.get("entry")
    if isinstance(entry, KOLRegistryEntry):
        return entry
    suggestions = [item["display_name"] for item in resolution["suggestions"]]
    message = f"KOL not found: {query}."
    if suggestions:
        message = (
            f"KOL not found or ambiguous: {query}. Close matches: {', '.join(suggestions[:3])}."
        )
    raise DomainError(
        message,
        code="KOL_AMBIGUOUS_QUERY" if resolution["ambiguous"] else "KOL_NOT_FOUND",
        metadata={
            "query": query,
            "suggestions": suggestions,
            "hint": resolution["hint"],
            "list_command": resolution["list_command"],
        },
    )


def add_mock_kol(
    display_name: str, aliases: list[str], allowed_symbols: list[str]
) -> dict[str, Any]:
    registry = _load_registry()
    kol_id = _slugify(display_name)
    if _exact_lookup(display_name, registry.kols) or _exact_lookup(kol_id, registry.kols):
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
    resolved = require_kol(kol_query)
    updated: KOLRegistryEntry | None = None
    for index, entry in enumerate(registry.kols):
        if entry.kol_id == resolved.kol_id:
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


def _rank_kol_matches(entries: list[KOLRegistryEntry], query: str) -> list[KOLLookupMatch]:
    normalized_query = _normalize_lookup_value(query)
    if not normalized_query:
        return []
    matches: list[KOLLookupMatch] = []
    for entry in entries:
        best: KOLLookupMatch | None = None
        for source_name, candidate in _lookup_candidates(entry):
            normalized_candidate = _normalize_lookup_value(candidate)
            if not normalized_candidate:
                continue
            score, matched_by = _candidate_score(normalized_query, normalized_candidate)
            if score <= 0:
                continue
            adjusted_score = min(score + _candidate_source_bonus(source_name), 1.0)
            current = KOLLookupMatch(
                entry=entry,
                score=adjusted_score,
                matched_by=matched_by
                if source_name == "display_name"
                else f"{matched_by}_{source_name}",
                matched_value=candidate,
            )
            if best is None or current.score > best.score:
                best = current
        if best is not None:
            matches.append(best)
    matches.sort(
        key=lambda item: (
            -item.score,
            item.entry.status != KOLStatus.ACTIVE,
            item.entry.display_name.lower(),
        )
    )
    return matches


def _exact_lookup(
    query: str,
    entries: list[KOLRegistryEntry] | None = None,
) -> KOLRegistryEntry | None:
    normalized_query = _normalize_lookup_value(query)
    if not normalized_query:
        return None
    for entry in entries or _load_registry().kols:
        for _, candidate in _lookup_candidates(entry):
            if normalized_query == _normalize_lookup_value(candidate):
                return entry
    return None


def _lookup_candidates(entry: KOLRegistryEntry) -> list[tuple[str, str]]:
    return [
        ("display_name", entry.display_name),
        ("kol_id", entry.kol_id),
        *[("alias", alias) for alias in entry.aliases],
    ]


def _candidate_score(normalized_query: str, normalized_candidate: str) -> tuple[float, str]:
    if normalized_query == normalized_candidate:
        return 1.0, "exact"
    if normalized_query in normalized_candidate:
        if len(normalized_query) < 3:
            return 0.0, "none"
        ratio = len(normalized_query) / max(len(normalized_candidate), 1)
        return min(0.84 + ratio * 0.16, 0.97), "substring"
    if normalized_candidate in normalized_query:
        if len(normalized_candidate) < 4:
            return 0.0, "none"
        ratio = len(normalized_candidate) / max(len(normalized_query), 1)
        if ratio < 0.45:
            return 0.0, "none"
        return min(0.78 + ratio * 0.12, 0.9), "superstring"
    score = SequenceMatcher(None, normalized_query, normalized_candidate).ratio()
    if score < 0.62:
        return 0.0, "none"
    return score, "fuzzy"


def _candidate_source_bonus(source_name: str) -> float:
    if source_name == "display_name":
        return 0.03
    if source_name == "alias":
        return 0.015
    return 0.0


def _should_auto_match(query: str, matches: list[KOLLookupMatch]) -> bool:
    if not matches:
        return False
    normalized_query = _normalize_lookup_value(query)
    best = matches[0]
    if best.score >= 0.995:
        return True
    second_score = matches[1].score if len(matches) > 1 else 0.0
    margin = best.score - second_score
    if best.score >= 0.91 and margin >= 0.07 and len(normalized_query) >= 4:
        return True
    return best.score >= 0.87 and margin >= 0.12 and len(normalized_query) >= 6


def _suggestion_payload(matches: list[KOLLookupMatch], limit: int) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in matches:
        if match.entry.kol_id in seen or match.score < 0.6:
            continue
        seen.add(match.entry.kol_id)
        suggestions.append(
            {
                "kol_id": match.entry.kol_id,
                "display_name": match.entry.display_name,
                "status": match.entry.status,
                "score": round(match.score, 3),
            }
        )
        if len(suggestions) >= limit:
            break
    return suggestions


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
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return "".join(char for char in normalized if char.isalnum())


def _slugify(display_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", display_name.strip()).strip("_").lower()
    if not normalized.startswith("kol_"):
        normalized = f"kol_{normalized}"
    return normalized


def _now() -> datetime:
    return datetime.now(UTC)
