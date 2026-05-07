from __future__ import annotations

from statistics import mean

from crypto_helper.core.evidence_store import (
    query_news,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.core.profile_service import get_profile
from crypto_helper.core.registry_service import get_active_kols, require_kol
from crypto_helper.models.evidence import EvidenceRef, TradeCall
from crypto_helper.models.registry import KOLTier
from crypto_helper.models.stats import KOLPerformance, KOLRankingItem, StatsResult


def compare_kols(
    symbol: str | None = None,
    time_range: str = "30d",
    include_dynamic: bool = True,
) -> StatsResult:
    rankings: list[KOLRankingItem] = []
    evidence_refs: list[EvidenceRef] = []
    for entry in get_active_kols():
        if not include_dynamic and entry.tier == KOLTier.DYNAMIC:
            continue
        calls = query_trade_calls(kol_query=entry.kol_id, symbol=symbol, time_range=time_range)
        if not calls:
            continue
        performance = _build_performance(entry.kol_id, entry.display_name, entry.tier, calls)
        rankings.append(
            KOLRankingItem(
                kol_id=entry.kol_id,
                display_name=entry.display_name,
                score=_score_from_metrics(performance.metrics),
                sample_size=performance.sample_size,
                metrics=performance.metrics,
                evidence_refs=performance.evidence_refs,
                limitations=performance.limitations,
                confidence=performance.confidence,
            )
        )
        evidence_refs.extend(performance.evidence_refs[:2])
    rankings.sort(key=lambda item: item.score, reverse=True)
    limitations = _shared_limitations(rankings)
    return StatsResult(
        title=f"KOL comparison for {symbol or 'all symbols'} over {time_range}",
        sample_size=sum(item.sample_size for item in rankings),
        metrics={"ranked_kols": len(rankings), "symbol": symbol or "all", "time_range": time_range},
        rankings=rankings,
        evidence_refs=evidence_refs[:8],
        limitations=limitations,
        metadata={"include_dynamic": include_dynamic},
    )


def get_kol_performance(
    kol_query: str,
    symbol: str | None = None,
    time_range: str = "30d",
) -> StatsResult:
    entry = require_kol(kol_query)
    calls = query_trade_calls(kol_query=entry.kol_id, symbol=symbol, time_range=time_range)
    performance = _build_performance(entry.kol_id, entry.display_name, entry.tier, calls)
    return StatsResult(
        title=f"Performance snapshot for {entry.display_name}",
        sample_size=performance.sample_size,
        metrics={"symbol": symbol or "all", "time_range": time_range},
        evidence_refs=performance.evidence_refs,
        limitations=performance.limitations,
        performance=performance,
        metadata={"kol_id": entry.kol_id},
    )


def get_active_symbols(kol_query: str) -> StatsResult:
    entry = require_kol(kol_query)
    profile_payload = get_profile(entry.kol_id)
    profile = profile_payload["profile"]
    evidence = search_evidence(kol_query=entry.kol_id, limit=5)
    return StatsResult(
        title=f"Active symbols for {entry.display_name}",
        sample_size=len(profile.active_symbols),
        metrics={"symbol_count": len(profile.active_symbols)},
        evidence_refs=evidence.items,
        limitations=profile_payload["limitations"],
        metadata={"symbols": profile.active_symbols},
    )


def get_market_summary(symbol: str | None = None, time_range: str = "1d") -> StatsResult:
    news_items = query_news(symbol=symbol, time_range=time_range)
    opinions = query_opinions(symbol=symbol, time_range=time_range)
    calls = query_trade_calls(symbol=symbol, time_range=time_range)
    symbol_counts: dict[str, int] = {}
    evidence_refs: list[EvidenceRef] = []
    for news_item in news_items:
        symbol_counts[news_item.symbol] = symbol_counts.get(news_item.symbol, 0) + 1
    for opinion in opinions:
        symbol_counts[opinion.symbol] = symbol_counts.get(opinion.symbol, 0) + 1
    for trade_call in calls:
        symbol_counts[trade_call.symbol] = symbol_counts.get(trade_call.symbol, 0) + 1
    evidence_refs.extend(
        [
            EvidenceRef(
                evidence_id=item.evidence_id,
                source_type="news",
                source_id=item.id,
                kol_id=None,
                symbol=item.symbol,
                timestamp=item.timestamp,
                channel_scope=item.channel_scope,
                summary=item.summary,
                confidence=item.confidence,
            )
            for item in news_items
        ]
    )
    evidence_refs.extend(
        [
            EvidenceRef(
                evidence_id=item.evidence_id,
                source_type="opinion",
                source_id=item.id,
                kol_id=item.kol_id,
                symbol=item.symbol,
                timestamp=item.timestamp,
                channel_scope=item.channel_scope,
                summary=item.summary,
                confidence=item.confidence,
            )
            for item in opinions
        ]
    )
    evidence_refs.extend(
        [
            EvidenceRef(
                evidence_id=item.evidence_id,
                source_type="trade_call",
                source_id=item.id,
                kol_id=item.kol_id,
                symbol=item.symbol,
                timestamp=item.timestamp,
                channel_scope=item.channel_scope,
                summary=item.summary,
                confidence=item.confidence,
            )
            for item in calls
        ]
    )
    top_symbols = [
        symbol_name
        for symbol_name, _ in sorted(symbol_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    limitations = ["Historical mock market snapshot only; not live market data."]
    return StatsResult(
        title=f"Market summary for {symbol or 'all symbols'} over {time_range}",
        sample_size=len(news_items) + len(opinions) + len(calls),
        metrics={
            "news_count": len(news_items),
            "opinion_count": len(opinions),
            "trade_call_count": len(calls),
        },
        evidence_refs=evidence_refs[:10],
        limitations=limitations,
        metadata={"top_symbols": top_symbols},
    )


def _build_performance(
    kol_id: str,
    display_name: str,
    tier: KOLTier,
    calls: list[TradeCall],
) -> KOLPerformance:
    sample_size = len(calls)
    outcomes = [call.outcome_score for call in calls if call.outcome_score is not None]
    win_rate = sum(1 for score in outcomes if score > 0) / len(outcomes) if outcomes else 0.0
    average_outcome = mean(outcomes) if outcomes else 0.0
    conviction = mean([call.confidence for call in calls]) if calls else 0.0
    metrics = {
        "win_rate": round(win_rate, 3),
        "average_outcome": round(average_outcome, 3),
        "average_confidence": round(conviction, 3),
    }
    limitations: list[str] = []
    if sample_size < 3:
        limitations.append("Small sample size reduces confidence.")
    if tier == KOLTier.DYNAMIC:
        limitations.append("Dynamic KOL ranking is less stable because evidence is sparse.")
    confidence = round(min(max(0.35 + sample_size * 0.12 + conviction * 0.2, 0.2), 0.9), 2)
    refs = [
        EvidenceRef(
            evidence_id=call.evidence_id,
            source_type="trade_call",
            source_id=call.id,
            kol_id=call.kol_id,
            symbol=call.symbol,
            timestamp=call.timestamp,
            channel_scope=call.channel_scope,
            summary=call.summary,
            confidence=call.confidence,
        )
        for call in calls[:5]
    ]
    return KOLPerformance(
        kol_id=kol_id,
        display_name=display_name,
        sample_size=sample_size,
        metrics=metrics,
        evidence_refs=refs,
        limitations=limitations,
        confidence=confidence,
    )


def _score_from_metrics(metrics: dict[str, float]) -> float:
    win_rate = metrics.get("win_rate", 0.0)
    average_outcome = metrics.get("average_outcome", 0.0)
    normalized_outcome = (average_outcome + 1.0) / 2.0
    return round(win_rate * 0.7 + normalized_outcome * 0.3, 3)


def _shared_limitations(rankings: list[KOLRankingItem]) -> list[str]:
    if not rankings:
        return ["No matching KOL performance data found."]
    limitations = ["Historical statistics only; not investment advice."]
    if any(item.sample_size < 3 for item in rankings):
        limitations.append("One or more KOLs have limited sample sizes in the selected window.")
    return limitations
