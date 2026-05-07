from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from crypto_helper.core.data_loader import append_jsonl, load_json, save_json
from crypto_helper.core.evidence_store import (
    query_events,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.core.registry_service import require_kol
from crypto_helper.models.evidence import EvidenceRef, KOLOpinion, TradeCall, TradeCallEvent
from crypto_helper.models.persona import KOLProfile
from crypto_helper.models.registry import KOLStatus


def get_profile(kol_query: str) -> dict[str, Any]:
    entry = require_kol(kol_query)
    profile = _load_profile_for_entry(entry.profile_path)
    limitations = list(profile.limitations)
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append("This KOL is archived; profile is historical only.")
    return {"profile": profile, "limitations": limitations}


def refresh_profile(kol_query: str) -> dict[str, Any]:
    entry = require_kol(kol_query)
    trade_calls = query_trade_calls(kol_query=entry.kol_id, time_range="90d")
    events = query_events(kol_query=entry.kol_id, time_range="90d")
    opinions = query_opinions(kol_query=entry.kol_id, time_range="90d")
    evidence = search_evidence(kol_query=entry.kol_id, limit=20)
    symbols = _rank_active_symbols(trade_calls, opinions, entry.allowed_symbols)
    trade_style = _derive_trade_style(events, evidence.items)
    reliability = _derive_reliability(trade_calls, evidence.items)
    limitations = list(evidence.limitations)
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append("Archived KOL profile refresh is based on historical data only.")
    if entry.status == KOLStatus.DISABLED:
        limitations.append("Disabled KOL profile remains available for registry administration.")
    profile = KOLProfile(
        kol_id=entry.kol_id,
        summary=_build_profile_summary(entry.display_name, trade_style, symbols, reliability),
        active_symbols=symbols,
        trade_style=trade_style,
        reliability=reliability,
        evidence_strength=len(evidence.items),
        last_refreshed=_now(),
        limitations=limitations,
    )
    save_json(entry.profile_path, profile.model_dump(mode="json"))
    audit_record = {
        "timestamp": _now(),
        "kol_id": entry.kol_id,
        "active_symbols": symbols,
        "trade_style": trade_style,
        "reliability": reliability,
        "mock_only": True,
    }
    audit_path = append_jsonl("audit/profile_updates.jsonl", audit_record)
    return {
        "profile": profile,
        "summary": {
            "active_symbols": symbols,
            "trade_style": trade_style,
            "reliability": reliability,
        },
        "mock_only": True,
        "audit_path": str(audit_path),
    }


def _load_profile_for_entry(relative_path: str) -> KOLProfile:
    raw = load_json(relative_path)
    return KOLProfile.model_validate(raw)


def _rank_active_symbols(
    trade_calls: Sequence[TradeCall],
    opinions: Sequence[KOLOpinion],
    fallback_symbols: list[str],
) -> list[str]:
    symbol_scores: dict[str, int] = {}
    for trade_call in trade_calls:
        symbol_scores[trade_call.symbol] = symbol_scores.get(trade_call.symbol, 0) + 2
    for opinion in opinions:
        symbol_scores[opinion.symbol] = symbol_scores.get(opinion.symbol, 0) + 1
    if not symbol_scores:
        for symbol in fallback_symbols:
            symbol_scores[symbol] = 1
    return [
        symbol for symbol, _ in sorted(symbol_scores.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


def _derive_trade_style(
    events: Sequence[TradeCallEvent],
    evidence_items: Sequence[EvidenceRef],
) -> list[str]:
    styles: list[str] = []
    event_types = {event.event_type for event in events}
    if "move_to_breakeven" in event_types:
        styles.append("move_sl_to_breakeven")
    if "partial_close" in event_types:
        styles.append("takes_partial_profit")
    summaries = " ".join(item.summary.lower() for item in evidence_items)
    if "reclaim" in summaries:
        styles.append("waits_for_reclaim")
    if "invalidation" in summaries:
        styles.append("invalidation_first")
    if not styles:
        styles.append("evidence_limited")
    return styles


def _derive_reliability(
    trade_calls: Sequence[TradeCall],
    evidence_items: Sequence[EvidenceRef],
) -> float:
    scores = [call.outcome_score for call in trade_calls if call.outcome_score is not None]
    if scores:
        normalized = [float((score + 1.0) / 2.0) for score in scores]
        base = mean(normalized)
    else:
        base = 0.45
    base += min(len(evidence_items), 10) * 0.01
    return round(min(max(base, 0.25), 0.92), 2)


def _build_profile_summary(
    display_name: str,
    trade_style: list[str],
    active_symbols: list[str],
    reliability: float,
) -> str:
    style_text = ", ".join(trade_style)
    symbol_text = ", ".join(active_symbols) if active_symbols else "no active symbols"
    return (
        f"{display_name} focuses on {symbol_text}, shows {style_text}, and currently maps to "
        f"reliability {reliability:.2f} in this mock snapshot."
    )


def _now() -> datetime:
    return datetime.now(UTC)
