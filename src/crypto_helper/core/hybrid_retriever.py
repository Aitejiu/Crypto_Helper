from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TypeVar

from crypto_helper.core.evidence_store import (
    collect_all_kol_evidence,
    query_events,
    query_news,
    query_opinions,
    query_trade_calls,
    search_evidence,
)
from crypto_helper.core.registry_service import require_kol
from crypto_helper.core.vector_store import VectorStore
from crypto_helper.models.evidence import (
    EvidenceRef,
    EvidenceSearchResult,
    KOLOpinion,
    MarketNews,
    TradeCall,
    TradeCallEvent,
)

T = TypeVar("T", bound=EvidenceRef)


def hybrid_search_evidence(
    kol_query: str | None = None,
    symbol: str | None = None,
    query: str | None = None,
    source_type: str | None = None,
    limit: int = 5,
    time_range: str | None = None,
) -> EvidenceSearchResult:
    if not query:
        return search_evidence(
            kol_query=kol_query,
            symbol=symbol,
            query=query,
            source_type=source_type,
            limit=limit,
        )

    structured_candidates = _collect_structured_candidates(
        kol_query=kol_query,
        symbol=symbol,
        source_type=source_type,
        time_range=time_range,
    )
    if not structured_candidates:
        return EvidenceSearchResult(
            items=[],
            limitations=["No evidence matched the requested filters."],
            query=_query_payload(kol_query, symbol, query, source_type, time_range, limit),
            total=0,
        )

    candidate_map = {item.evidence_id: item for item in structured_candidates}
    vector_results = []
    limitations: list[str] = []
    vector_store = VectorStore()
    try:
        vector_results = vector_store.search(
            query,
            top_k=max(limit * 4, 10),
            filters=_vector_filters(kol_query, symbol, source_type),
        )
    except Exception:
        limitations.append("Vector retrieval unavailable; used structured fallback.")
        vector_results = []

    vector_score_map = {
        result.evidence_id: result.score
        for result in vector_results
        if result.evidence_id in candidate_map
    }
    ranked = _rank_candidates(
        list(candidate_map.values()),
        entry_kol_id=require_kol(kol_query).kol_id if kol_query else None,
        symbol=symbol.upper() if symbol else None,
        vector_score_map=vector_score_map,
    )
    items = ranked[:limit]
    if not items:
        limitations.append("No evidence matched the requested filters.")
    elif len(items) < limit:
        limitations.append("Evidence base is limited for the requested query.")
    return EvidenceSearchResult(
        items=items,
        limitations=limitations,
        query=_query_payload(kol_query, symbol, query, source_type, time_range, limit),
        total=len(ranked),
    )


def _collect_structured_candidates(
    *,
    kol_query: str | None,
    symbol: str | None,
    source_type: str | None,
    time_range: str | None,
) -> list[EvidenceRef]:
    entry_kol_id = require_kol(kol_query).kol_id if kol_query else None
    symbol_upper = symbol.upper() if symbol else None
    evidence_map = collect_all_kol_evidence()
    evidence_items: list[EvidenceRef] = []
    for current_kol_id, items in evidence_map.items():
        if entry_kol_id is not None and current_kol_id != entry_kol_id:
            continue
        evidence_items.extend(
            item
            for item in _filter_by_time_range(items, time_range)
            if (symbol_upper is None or item.symbol == symbol_upper)
            and (source_type is None or item.source_type == source_type)
        )
    trade_calls = query_trade_calls(
        kol_query=entry_kol_id, symbol=symbol_upper, time_range=time_range
    )
    events = query_events(kol_query=entry_kol_id, symbol=symbol_upper, time_range=time_range)
    opinions = query_opinions(kol_query=entry_kol_id, symbol=symbol_upper, time_range=time_range)
    news = query_news(symbol=symbol_upper, time_range=time_range)
    if source_type in {None, "trade_call"}:
        evidence_items.extend(_refs_from_trade_calls(trade_calls))
    if source_type in {None, "event"}:
        evidence_items.extend(_refs_from_events(events))
    if source_type in {None, "opinion", "market_analysis"}:
        evidence_items.extend(_refs_from_opinions(opinions, source_type))
    if source_type in {None, "news"}:
        evidence_items.extend(_refs_from_news(news))
    deduped: dict[str, EvidenceRef] = {}
    for item in evidence_items:
        if (
            entry_kol_id is not None
            and item.kol_id not in {None, entry_kol_id}
            and item.source_type != "news"
        ):
            continue
        deduped[item.evidence_id] = item
    return list(deduped.values())


def _rank_candidates(
    candidates: list[EvidenceRef],
    *,
    entry_kol_id: str | None,
    symbol: str | None,
    vector_score_map: dict[str, float],
) -> list[EvidenceRef]:
    latest_timestamp = max((item.timestamp for item in candidates), default=datetime.min)
    scored: list[tuple[float, EvidenceRef]] = []
    for item in candidates:
        score = 0.0
        if entry_kol_id and item.kol_id == entry_kol_id:
            score += 30.0
        if symbol and item.symbol == symbol:
            score += 20.0
        score += vector_score_map.get(item.evidence_id, 0.0) * 25.0
        score += item.confidence * 10.0
        age_delta = latest_timestamp - item.timestamp
        score += max(0.0, 3.0 - age_delta.total_seconds() / 86400 / 14)
        scored.append((score, item))
    scored.sort(key=lambda pair: (pair[0], pair[1].confidence, pair[1].timestamp), reverse=True)
    return [item for _, item in scored]


def _refs_from_trade_calls(calls: list[TradeCall]) -> list[EvidenceRef]:
    return [
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
        for call in calls
    ]


def _refs_from_events(events: list[TradeCallEvent]) -> list[EvidenceRef]:
    return [
        EvidenceRef(
            evidence_id=event.evidence_id,
            source_type="event",
            source_id=event.id,
            kol_id=event.kol_id,
            symbol=event.symbol,
            timestamp=event.timestamp,
            channel_scope=event.channel_scope,
            summary=event.summary,
            confidence=event.confidence,
        )
        for event in events
    ]


def _refs_from_opinions(
    opinions: list[KOLOpinion], requested_source_type: str | None
) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for opinion in opinions:
        source_kind = (
            "market_analysis"
            if opinion.evidence_id.startswith("import_market_analysis_")
            else "opinion"
        )
        if requested_source_type is not None and source_kind != requested_source_type:
            continue
        refs.append(
            EvidenceRef(
                evidence_id=opinion.evidence_id,
                source_type=source_kind,
                source_id=opinion.id,
                kol_id=opinion.kol_id,
                symbol=opinion.symbol,
                timestamp=opinion.timestamp,
                channel_scope=opinion.channel_scope,
                summary=opinion.summary,
                confidence=opinion.confidence,
            )
        )
    return refs


def _refs_from_news(items: list[MarketNews]) -> list[EvidenceRef]:
    return [
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
        for item in items
    ]


def _filter_by_time_range(items: list[T], time_range: str | None) -> list[T]:
    if not time_range or not items:
        return sorted(items, key=lambda item: item.timestamp, reverse=True)
    delta = _parse_time_range(time_range)
    anchor = max(item.timestamp for item in items)
    cutoff = anchor - delta
    return sorted(
        [item for item in items if item.timestamp >= cutoff],
        key=lambda item: item.timestamp,
        reverse=True,
    )


def _parse_time_range(time_range: str) -> timedelta:
    count = int(time_range[:-1])
    unit = time_range[-1]
    if unit == "d":
        return timedelta(days=count)
    if unit == "h":
        return timedelta(hours=count)
    if unit == "w":
        return timedelta(weeks=count)
    raise ValueError(f"Unsupported time range: {time_range}")


def _vector_filters(
    kol_query: str | None,
    symbol: str | None,
    source_type: str | None,
) -> dict[str, Any] | None:
    filters: dict[str, Any] = {}
    if kol_query:
        filters["kol_id"] = require_kol(kol_query).kol_id
    if symbol:
        filters["symbol"] = symbol.upper()
    if source_type:
        filters["source_type"] = source_type
    return filters or None


def _query_payload(
    kol_query: str | None,
    symbol: str | None,
    query: str | None,
    source_type: str | None,
    time_range: str | None,
    limit: int,
) -> dict[str, Any]:
    return {
        "kol_query": kol_query,
        "symbol": symbol.upper() if symbol else None,
        "query": query,
        "source_type": source_type,
        "time_range": time_range,
        "limit": limit,
    }
