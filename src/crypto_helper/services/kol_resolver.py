from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from crypto_helper.core.data_loader import load_json
from crypto_helper.models.common import DomainError
from crypto_helper.models.registry import KOLRegistry, KOLRegistryEntry, KOLStatus
from crypto_helper.request_context import RequestContext


@dataclass(frozen=True)
class KOLLookupMatch:
    entry: KOLRegistryEntry
    score: float
    matched_by: str
    matched_value: str


def resolve_kol(
    query: str,
    platform: str | None = None,
    registry: KOLRegistry | list[KOLRegistryEntry] | None = None,
    request_context: RequestContext | None = None,
    suggestion_limit: int = 5,
) -> dict[str, Any]:
    del request_context
    entries = _coerce_entries(registry)
    alias_overrides = _load_alias_overrides()
    platform_handles = _load_platform_handles()
    matches = _rank_kol_matches(entries, query, platform, alias_overrides, platform_handles)
    alternatives = _alternatives_payload(matches, suggestion_limit)
    if not matches:
        return {
            "status": "not_found",
            "kol_id": None,
            "display_name": None,
            "confidence": 0.0,
            "matched_by": None,
            "matched_value": None,
            "alternatives": alternatives,
            "entry": None,
        }

    best = matches[0]
    if _should_auto_match(query, matches):
        return {
            "status": "resolved",
            "kol_id": best.entry.kol_id,
            "display_name": best.entry.display_name,
            "confidence": round(best.score, 3),
            "matched_by": best.matched_by,
            "matched_value": best.matched_value,
            "alternatives": alternatives,
            "entry": best.entry,
        }

    return {
        "status": "ambiguous",
        "kol_id": None,
        "display_name": None,
        "confidence": round(best.score, 3),
        "matched_by": None,
        "matched_value": None,
        "alternatives": alternatives,
        "entry": None,
    }


def _coerce_entries(
    registry: KOLRegistry | list[KOLRegistryEntry] | None,
) -> list[KOLRegistryEntry]:
    if registry is None:
        raw = load_json("registry/kols.json")
        return KOLRegistry.model_validate(raw).kols
    if isinstance(registry, KOLRegistry):
        return registry.kols
    return registry


def _rank_kol_matches(
    entries: list[KOLRegistryEntry],
    query: str,
    platform: str | None,
    alias_overrides: dict[str, list[str]],
    platform_handles: dict[str, dict[str, str]],
) -> list[KOLLookupMatch]:
    normalized_query = _normalize_lookup_value(query)
    if not normalized_query:
        return []
    matches: list[KOLLookupMatch] = []
    for entry in entries:
        best: KOLLookupMatch | None = None
        for source_name, candidate in _lookup_candidates(
            entry,
            platform=platform,
            alias_overrides=alias_overrides,
            platform_handles=platform_handles,
        ):
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


def _lookup_candidates(
    entry: KOLRegistryEntry,
    *,
    platform: str | None,
    alias_overrides: dict[str, list[str]],
    platform_handles: dict[str, dict[str, str]],
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [
        ("display_name", entry.display_name),
        ("kol_id", entry.kol_id),
    ]
    seen = {_normalize_lookup_value(entry.display_name), _normalize_lookup_value(entry.kol_id)}
    handle_keys = _platform_handle_keys(platform)
    for source_name, handle in platform_handles.get(entry.kol_id, {}).items():
        if handle_keys is not None and source_name not in handle_keys:
            continue
        normalized = _normalize_lookup_value(handle)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append((source_name, handle))
    for alias in [*entry.aliases, *alias_overrides.get(entry.kol_id, [])]:
        normalized = _normalize_lookup_value(alias)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(("alias", alias))
    return candidates


def _load_alias_overrides() -> dict[str, list[str]]:
    try:
        raw = load_json("registry/aliases.json")
    except DomainError:
        return {}
    if isinstance(raw, dict):
        if "aliases" in raw and isinstance(raw["aliases"], dict):
            raw = raw["aliases"]
        if all(isinstance(value, list) for value in raw.values()):
            return {
                str(kol_id): [str(alias) for alias in aliases]
                for kol_id, aliases in raw.items()
                if isinstance(aliases, list)
            }
    if isinstance(raw, list):
        result: dict[str, list[str]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            kol_id = item.get("kol_id")
            aliases = item.get("aliases")
            if isinstance(kol_id, str) and isinstance(aliases, list):
                result[kol_id] = [str(alias) for alias in aliases]
        return result
    return {}


def _load_platform_handles() -> dict[str, dict[str, str]]:
    try:
        raw = load_json("registry/platforms.json")
    except DomainError:
        return {}
    normalized: dict[str, dict[str, str]] = {}
    payload: Any = raw.get("platforms", raw) if isinstance(raw, dict) else raw
    if isinstance(payload, dict):
        for kol_id, handle_map in payload.items():
            if not isinstance(handle_map, dict):
                continue
            normalized[str(kol_id)] = {
                str(key): str(value)
                for key, value in handle_map.items()
                if value is not None and str(value).strip()
            }
    elif isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            kol_id = item.get("kol_id")
            if not isinstance(kol_id, str):
                continue
            normalized[kol_id] = {
                str(key): str(value)
                for key, value in item.items()
                if key != "kol_id" and value is not None and str(value).strip()
            }
    return normalized


def _platform_handle_keys(platform: str | None) -> set[str] | None:
    if platform is None:
        return None
    normalized = platform.strip().lower()
    if normalized == "twitter":
        return {"twitter_handle"}
    if normalized == "telegram":
        return {"telegram_handle"}
    if normalized == "discord":
        return {"discord_handle"}
    return {normalized, f"{normalized}_handle"}


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
    if source_name.endswith("_handle"):
        return 0.025
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


def _alternatives_payload(matches: list[KOLLookupMatch], limit: int) -> list[dict[str, Any]]:
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
                "matched_by": match.matched_by,
            }
        )
        if len(suggestions) >= limit:
            break
    return suggestions


def _normalize_lookup_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return "".join(char for char in normalized if char.isalnum())
