from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from crypto_helper.core.evidence_store import (
    query_events,
    query_news,
    query_opinions,
    query_trade_calls,
)
from crypto_helper.core.profile_service import get_profile
from crypto_helper.core.registry_service import require_kol
from crypto_helper.core.stats_service import get_kol_performance, get_market_summary
from crypto_helper.models.common import DomainError
from crypto_helper.models.evidence import EvidenceRef, KOLOpinion, TradeCallEvent
from crypto_helper.models.registry import KOLStatus, KOLTier
from crypto_helper.models.report import ReportResult


def generate_kol_report(kol_query: str, time_range: str = "7d") -> ReportResult:
    entry = require_kol(kol_query)
    if entry.status == KOLStatus.DISABLED:
        raise DomainError(
            f"{entry.display_name} is disabled and unavailable for reporting.",
            code="KOL_DISABLED",
        )
    profile_payload = get_profile(entry.kol_id)
    profile = profile_payload["profile"]
    performance = get_kol_performance(entry.kol_id, time_range=time_range).performance
    if performance is None:
        raise DomainError("Missing performance data for report.", code="REPORT_DATA_MISSING")
    trade_calls = query_trade_calls(kol_query=entry.kol_id, time_range=time_range)
    events = query_events(kol_query=entry.kol_id, time_range=time_range)
    opinions = query_opinions(kol_query=entry.kol_id, time_range=time_range)
    evidence_refs = [*performance.evidence_refs]
    evidence_refs.extend(_refs_from_events(events))
    evidence_refs.extend(_refs_from_opinions(opinions))
    limitations = list(performance.limitations)
    limitations.extend(profile_payload["limitations"])
    if entry.status == KOLStatus.ARCHIVED:
        limitations.append("Archived KOL report is historical only.")
    if entry.tier == KOLTier.DYNAMIC and profile.evidence_strength < 4:
        limitations.append("Dynamic KOL report has low confidence because evidence is sparse.")
    markdown = "\n".join(
        [
            f"# {entry.display_name} {time_range} Report",
            "",
            "## KOL Summary",
            profile.summary,
            "",
            "## SOUL Summary",
            f"Trade style: {', '.join(profile.trade_style)}",
            "",
            "## Active Symbols",
            ", ".join(profile.active_symbols) if profile.active_symbols else "None",
            "",
            "## Recent Trade Calls",
            *_bullet_lines(call.summary for call in trade_calls[:5]),
            "",
            "## Recent Events",
            *_bullet_lines(event.summary for event in events[:5]),
            "",
            "## Opinion Summary",
            *_bullet_lines(opinion.summary for opinion in opinions[:5]),
            "",
            "## Reliability",
            (
                f"Sample size {performance.sample_size}, win rate "
                f"{performance.metrics['win_rate']}, average outcome "
                f"{performance.metrics['average_outcome']}."
            ),
            "",
            "## Limitations",
            *_bullet_lines(limitations or ["Historical mock data only."]),
            "",
            "## Evidence Appendix",
            *_evidence_appendix(evidence_refs),
        ]
    )
    return ReportResult(
        title=f"{entry.display_name} report",
        markdown=markdown,
        evidence_refs=evidence_refs,
        limitations=limitations,
        metadata={"kol_id": entry.kol_id, "time_range": time_range},
    )


def generate_daily_market_report(time_range: str = "1d") -> ReportResult:
    summary = get_market_summary(time_range=time_range)
    news_items = query_news(time_range=time_range)
    opinions = query_opinions(time_range=time_range)
    calls = query_trade_calls(time_range=time_range)
    symbol_counter: Counter[str] = Counter()
    for news_item in news_items:
        symbol_counter[news_item.symbol] += 1
    for opinion in opinions:
        symbol_counter[opinion.symbol] += 1
    for trade_call in calls:
        symbol_counter[trade_call.symbol] += 1
    top_symbols = [symbol for symbol, _ in symbol_counter.most_common(5)]
    evidence_refs = list(summary.evidence_refs)
    limitations = list(summary.limitations)
    markdown = "\n".join(
        [
            f"# Daily Market Report ({time_range})",
            "",
            "## Top Symbols",
            ", ".join(top_symbols) if top_symbols else "No strong symbol concentration",
            "",
            "## Important Trade Calls",
            *_bullet_lines(call.summary for call in calls[:5]),
            "",
            "## Recent Events",
            *_bullet_lines(
                ref.summary for ref in summary.evidence_refs if ref.source_type == "trade_call"
            ),
            "",
            "## Market News",
            *_bullet_lines(item.summary for item in news_items[:5]),
            "",
            "## KOL Opinions",
            *_bullet_lines(item.summary for item in opinions[:5]),
            "",
            "## Limitations",
            *_bullet_lines(limitations),
            "",
            "## Evidence Appendix",
            *_evidence_appendix(evidence_refs),
        ]
    )
    return ReportResult(
        title="Daily market report",
        markdown=markdown,
        evidence_refs=evidence_refs,
        limitations=limitations,
        metadata={"time_range": time_range, "top_symbols": top_symbols},
    )


def _refs_from_events(events: list[TradeCallEvent]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for event in events:
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


def _refs_from_opinions(opinions: list[KOLOpinion]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for opinion in opinions:
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


def _bullet_lines(lines: Iterable[str]) -> list[str]:
    rendered = [f"- {line}" for line in lines if line]
    return rendered or ["- None"]


def _evidence_appendix(refs: list[EvidenceRef]) -> list[str]:
    if not refs:
        return ["- No evidence references found"]
    return [f"- [{ref.evidence_id}] {ref.summary}" for ref in refs[:10]]
