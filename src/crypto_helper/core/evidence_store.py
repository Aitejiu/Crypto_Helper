from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TypeVar

from crypto_helper.core.data_loader import load_json
from crypto_helper.core.registry_service import require_kol
from crypto_helper.models.common import DomainError
from crypto_helper.models.evidence import (
    EvidenceRef,
    EvidenceSearchResult,
    KOLOpinion,
    MarketNews,
    TradeCall,
    TradeCallEvent,
)

T = TypeVar("T", TradeCall, TradeCallEvent, KOLOpinion, MarketNews, EvidenceRef)


def search_evidence(
    kol_query: str | None = None,
    symbol: str | None = None,
    query: str | None = None,
    source_type: str | None = None,
    limit: int = 5,
) -> EvidenceSearchResult:
    entry_kol_id: str | None = None
    if kol_query:
        entry_kol_id = require_kol(kol_query).kol_id
    query_terms = _keyword_terms(query)
    symbol_upper = symbol.upper() if symbol else None
    evidence_items = _collect_evidence_refs(entry_kol_id)
    scored: list[tuple[float, EvidenceRef]] = []
    latest_timestamp = max((item.timestamp for item in evidence_items), default=datetime.min)
    for item in evidence_items:
        if source_type and item.source_type != source_type:
            continue
        if symbol_upper and item.symbol != symbol_upper:
            continue
        score = 0.0
        if entry_kol_id and item.kol_id == entry_kol_id:
            score += 30
        if symbol_upper and item.symbol == symbol_upper:
            score += 20
        score += _keyword_score(item.summary, query_terms) * 10
        score += item.confidence * 5
        age_delta = latest_timestamp - item.timestamp
        score += max(0.0, 2.0 - age_delta.total_seconds() / 86400 / 14)
        if score > 0 or not query_terms:
            scored.append((score, item))
    scored.sort(key=lambda pair: (pair[0], pair[1].confidence, pair[1].timestamp), reverse=True)
    items = [item for _, item in scored[:limit]]
    limitations: list[str] = []
    if not items:
        limitations.append("No evidence matched the requested filters.")
    elif len(items) < limit:
        limitations.append("Evidence base is limited for the requested query.")
    return EvidenceSearchResult(
        items=items,
        limitations=limitations,
        query={
            "kol_query": kol_query,
            "symbol": symbol_upper,
            "query": query,
            "source_type": source_type,
            "limit": limit,
        },
        total=len(scored),
    )


def query_trade_calls(
    kol_query: str | None = None,
    symbol: str | None = None,
    status: str | None = None,
    time_range: str | None = None,
) -> list[TradeCall]:
    kol_id = require_kol(kol_query).kol_id if kol_query else None
    calls = _load_trade_calls()
    filtered = [
        call
        for call in calls
        if (kol_id is None or call.kol_id == kol_id)
        and (symbol is None or call.symbol == symbol.upper())
        and (status is None or call.status == status)
    ]
    return _filter_by_time_range(filtered, time_range)


def query_events(
    kol_query: str | None = None,
    symbol: str | None = None,
    event_type: str | None = None,
    time_range: str | None = None,
) -> list[TradeCallEvent]:
    kol_id = require_kol(kol_query).kol_id if kol_query else None
    events = _load_events()
    filtered = [
        event
        for event in events
        if (kol_id is None or event.kol_id == kol_id)
        and (symbol is None or event.symbol == symbol.upper())
        and (event_type is None or event.event_type == event_type)
    ]
    return _filter_by_time_range(filtered, time_range)


def query_opinions(
    kol_query: str | None = None,
    symbol: str | None = None,
    sentiment: str | None = None,
    time_range: str | None = None,
) -> list[KOLOpinion]:
    kol_id = require_kol(kol_query).kol_id if kol_query else None
    opinions = _load_opinions()
    filtered = [
        opinion
        for opinion in opinions
        if (kol_id is None or opinion.kol_id == kol_id)
        and (symbol is None or opinion.symbol == symbol.upper())
        and (sentiment is None or opinion.sentiment == sentiment)
    ]
    return _filter_by_time_range(filtered, time_range)


def query_news(
    symbol: str | None = None,
    importance: str | None = None,
    time_range: str | None = None,
) -> list[MarketNews]:
    news_items = _load_news()
    filtered = [
        item
        for item in news_items
        if (symbol is None or item.symbol == symbol.upper())
        and (importance is None or item.importance == importance)
    ]
    return _filter_by_time_range(filtered, time_range)


def collect_all_kol_evidence() -> dict[str, list[EvidenceRef]]:
    raw_registry = load_json("registry/kols.json")
    kols = raw_registry["kols"]
    result: dict[str, list[EvidenceRef]] = {}
    for item in kols:
        kol_id = str(item["kol_id"])
        raw = load_json(str(item["evidence_path"]))
        result[kol_id] = [EvidenceRef.model_validate(record) for record in raw.get("items", [])]
    return result


def _collect_evidence_refs(kol_id: str | None = None) -> list[EvidenceRef]:
    items: list[EvidenceRef] = []
    for current_kol_id, evidence_items in collect_all_kol_evidence().items():
        if kol_id is None or kol_id == current_kol_id:
            items.extend(evidence_items)
    items.extend(_trade_call_refs(kol_id))
    items.extend(_trade_event_refs(kol_id))
    items.extend(_opinion_refs(kol_id))
    items.extend(_news_refs())
    return items


def _load_trade_calls() -> list[TradeCall]:
    raw = load_json("mock/trade_calls.json")
    return [TradeCall.model_validate(item) for item in raw]


def _load_events() -> list[TradeCallEvent]:
    raw = load_json("mock/trade_call_events.json")
    return [TradeCallEvent.model_validate(item) for item in raw]


def _load_opinions() -> list[KOLOpinion]:
    raw = load_json("mock/opinions.json")
    return [KOLOpinion.model_validate(item) for item in raw]


def _load_news() -> list[MarketNews]:
    raw = load_json("mock/news.json")
    return [MarketNews.model_validate(item) for item in raw]


def _trade_call_refs(kol_id: str | None) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for call in _load_trade_calls():
        if kol_id and call.kol_id != kol_id:
            continue
        refs.append(
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
        )
    return refs


def _trade_event_refs(kol_id: str | None) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for event in _load_events():
        if kol_id and event.kol_id != kol_id:
            continue
        refs.append(
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
        )
    return refs


def _opinion_refs(kol_id: str | None) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for opinion in _load_opinions():
        if kol_id and opinion.kol_id != kol_id:
            continue
        refs.append(
            EvidenceRef(
                evidence_id=opinion.evidence_id,
                source_type="opinion",
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


def _news_refs() -> list[EvidenceRef]:
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
        for item in _load_news()
    ]


def _keyword_terms(query: str | None) -> list[str]:
    if not query:
        return []
    return [token for token in re.split(r"[\s,.;:!?()]+", query.lower()) if token]


def _keyword_score(summary: str, terms: list[str]) -> int:
    if not terms:
        return 0
    lowered = summary.lower()
    return sum(1 for term in terms if term in lowered)


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
    match = re.fullmatch(r"(?P<count>\d+)(?P<unit>[dhw])", time_range)
    if match is None:
        raise DomainError(f"Unsupported time range: {time_range}", code="INVALID_TIME_RANGE")
    count = int(match.group("count"))
    unit = match.group("unit")
    if unit == "d":
        return timedelta(days=count)
    if unit == "h":
        return timedelta(hours=count)
    if unit == "w":
        return timedelta(weeks=count)
    raise DomainError(f"Unsupported time range: {time_range}", code="INVALID_TIME_RANGE")
