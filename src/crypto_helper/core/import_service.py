from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_helper.core.data_loader import (
    append_jsonl,
    load_json_path,
    save_json,
    save_json_path,
    save_yaml,
)
from crypto_helper.core.paths import DATA_ENV_VAR, ensure_runtime_data
from crypto_helper.core.profile_service import refresh_profile
from crypto_helper.models.common import DomainError
from crypto_helper.models.evidence import KOLOpinion, MarketNews, TradeCall, TradeCallEvent
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

IMPORT_RULES_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "import_configs"
    / "core_table_import_rules.json"
)
AUTHOR_MAPPING_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "import_configs" / "kol_author_mappings.json"
)


@dataclass(frozen=True)
class CanonicalKOLMapping:
    display_name: str
    source_authors: tuple[str, ...]
    aliases: tuple[str, ...]
    kol_id: str | None = None


@dataclass(frozen=True)
class PendingImportSource:
    source_dir: Path
    cleanup_path: Path


@dataclass(frozen=True)
class ImportRules:
    ignored_authors: frozenset[str]
    quote_assets: tuple[str, ...]
    author_mappings: dict[str, CanonicalKOLMapping]
    canonical_mappings: dict[str, CanonicalKOLMapping]


def import_core_tables(
    source_dir: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    rules = _load_import_rules()
    source_root = _resolve_source_csv_dir(Path(source_dir))
    data_root = (
        Path(output_dir).expanduser().resolve() if output_dir else ensure_runtime_data().resolve()
    )
    mock_root = data_root / "mock"
    mock_root.mkdir(parents=True, exist_ok=True)
    stale_message_blocks = mock_root / "message_blocks.json"
    if stale_message_blocks.exists():
        stale_message_blocks.unlink()

    trade_call_rows = _read_csv(source_root / "kol_trade_calls.csv")
    trade_event_rows = _read_csv(source_root / "trade_call_events.csv")
    opinion_rows = _read_csv(source_root / "kol_opinions.csv")
    analysis_rows = _read_csv(source_root / "market_analysis.csv")
    news_rows = _read_csv(source_root / "market_news.csv")

    trade_calls, trade_summary = _build_trade_calls(trade_call_rows, rules)
    trade_lookup = {trade_call.id: trade_call for trade_call in trade_calls}
    trade_events, event_summary = _build_trade_call_events(trade_event_rows, trade_lookup)
    opinions, opinion_summary = _build_opinions(opinion_rows, rules)
    market_analyses, analysis_summary = _build_market_analyses(analysis_rows, rules)
    combined_opinions = sorted(
        [*opinions, *market_analyses],
        key=lambda item: item.timestamp,
        reverse=True,
    )
    news_items, news_summary = _build_news(news_rows)
    author_to_kol = dict(trade_summary["author_to_kol"])
    author_to_kol.update(opinion_summary["author_to_kol"])
    author_to_kol.update(analysis_summary["author_to_kol"])

    save_json_path(
        mock_root / "trade_calls.json", [item.model_dump(mode="json") for item in trade_calls]
    )
    save_json_path(
        mock_root / "trade_call_events.json",
        [item.model_dump(mode="json") for item in trade_events],
    )
    save_json_path(
        mock_root / "opinions.json",
        [item.model_dump(mode="json") for item in combined_opinions],
    )
    save_json_path(mock_root / "news.json", [item.model_dump(mode="json") for item in news_items])

    summary = {
        "source_dir": str(source_root),
        "output_dir": str(data_root),
        "files_written": {
            "mock/trade_calls.json": len(trade_calls),
            "mock/trade_call_events.json": len(trade_events),
            "mock/opinions.json": len(combined_opinions),
            "mock/news.json": len(news_items),
        },
        "ignored_authors": sorted(
            set(trade_summary["ignored_authors"])
            | set(opinion_summary["ignored_authors"])
            | set(analysis_summary["ignored_authors"])
        ),
        "candidate_kols": _build_candidate_kols(
            trade_calls,
            opinions,
            market_analyses,
            author_to_kol,
        ),
        "source_rows": {
            "kol_trade_calls.csv": len(trade_call_rows),
            "trade_call_events.csv": len(trade_event_rows),
            "kol_opinions.csv": len(opinion_rows),
            "market_analysis.csv": len(analysis_rows),
            "market_news.csv": len(news_rows),
        },
        "converted_rows": {
            "trade_calls": len(trade_calls),
            "trade_call_events": len(trade_events),
            "kol_opinions": len(opinions),
            "market_analyses": len(market_analyses),
            "opinions": len(combined_opinions),
            "news": len(news_items),
        },
        "dropped_rows": {
            "trade_calls": trade_summary["dropped_rows"],
            "trade_call_events": event_summary["dropped_rows"],
            "kol_opinions": opinion_summary["dropped_rows"],
            "market_analyses": analysis_summary["dropped_rows"],
            "news": news_summary["dropped_rows"],
        },
        "notes": [
            "This importer normalizes core tables into the mock layer only.",
            "Candidate KOL ids are generated from source authors for future registry promotion.",
            "market_analysis is merged into mock/opinions.json as structured analysis evidence.",
            "message_blocks and discord_messages remain source material and are not imported.",
        ],
    }
    save_json_path(data_root / "reports" / "imports" / "core_tables_import_summary.json", summary)
    return summary


def promote_imported_kols(
    source_dir: str | Path,
    output_dir: str | Path | None = None,
    min_signals: int = 1,
) -> dict[str, Any]:
    rules = _load_import_rules()
    core_summary = import_core_tables(source_dir=source_dir, output_dir=output_dir)
    data_root = Path(core_summary["output_dir"]).resolve()
    mock_root = data_root / "mock"

    registry = _load_registry_from_root(data_root)
    trade_calls = [
        TradeCall.model_validate(item) for item in load_json_path(mock_root / "trade_calls.json")
    ]
    trade_events = [
        TradeCallEvent.model_validate(item)
        for item in load_json_path(mock_root / "trade_call_events.json")
    ]
    opinions = [
        KOLOpinion.model_validate(item) for item in load_json_path(mock_root / "opinions.json")
    ]

    selected_candidates = [
        item
        for item in core_summary["candidate_kols"]
        if int(item["trade_calls"]) + int(item["opinions"]) + int(item["market_analyses"])
        >= min_signals
    ]
    if not selected_candidates:
        raise DomainError(
            "No import candidates met the promotion threshold.",
            code="IMPORT_NO_PROMOTION_CANDIDATES",
            metadata={"min_signals": min_signals},
        )

    id_map: dict[str, str] = {}
    promoted_entries: list[KOLRegistryEntry] = []
    updated_registry = list(registry.kols)

    for candidate in selected_candidates:
        legacy_kol_id = str(candidate["kol_id"])
        display_name = str(candidate["display_name"])
        new_kol_id = _resolve_promoted_kol_id(display_name, updated_registry, rules)
        id_map[legacy_kol_id] = new_kol_id
        allowed_symbols = [str(symbol) for symbol in candidate["symbols"]]
        aliases = _build_aliases(display_name, rules)
        updated_registry = _prune_duplicate_registry_entries(
            updated_registry,
            display_name=display_name,
            canonical_kol_id=new_kol_id,
            rules=rules,
        )
        existing_index = next(
            (index for index, entry in enumerate(updated_registry) if entry.kol_id == new_kol_id),
            None,
        )
        entry = KOLRegistryEntry(
            kol_id=new_kol_id,
            display_name=display_name,
            aliases=aliases,
            status=KOLStatus.ACTIVE,
            tier=KOLTier.DYNAMIC,
            persona_mode=PersonaMode.RUNTIME_ONLY,
            soul_path=f"kols/{new_kol_id}/soul.yaml",
            profile_path=f"kols/{new_kol_id}/profile.json",
            evidence_path=f"kols/{new_kol_id}/evidence.json",
            allowed_symbols=allowed_symbols,
            risk_level="unknown",
            last_updated=_now(),
        )
        if existing_index is None:
            updated_registry.append(entry)
        else:
            previous = updated_registry[existing_index]
            updated_registry[existing_index] = entry.model_copy(
                update={
                    "status": previous.status,
                    "tier": previous.tier,
                    "persona_mode": previous.persona_mode,
                }
            )
            entry = updated_registry[existing_index]
        promoted_entries.append(entry)

    updated_registry.sort(key=lambda item: item.kol_id)
    save_json_path(
        data_root / "registry" / "kols.json",
        KOLRegistry(kols=updated_registry).model_dump(mode="json"),
    )

    rewritten_trade_calls = [_rewrite_trade_call(call, id_map) for call in trade_calls]
    rewritten_trade_events = [_rewrite_trade_event(event, id_map) for event in trade_events]
    rewritten_opinions = [_rewrite_opinion(opinion, id_map) for opinion in opinions]
    save_json_path(
        mock_root / "trade_calls.json",
        [item.model_dump(mode="json") for item in rewritten_trade_calls],
    )
    save_json_path(
        mock_root / "trade_call_events.json",
        [item.model_dump(mode="json") for item in rewritten_trade_events],
    )
    save_json_path(
        mock_root / "opinions.json",
        [item.model_dump(mode="json") for item in rewritten_opinions],
    )

    with _data_dir_override(data_root):
        trade_events_by_kol: dict[str, list[TradeCallEvent]] = {}
        for event in rewritten_trade_events:
            trade_events_by_kol.setdefault(event.kol_id, []).append(event)

        opinions_by_kol: dict[str, list[KOLOpinion]] = {}
        for opinion in rewritten_opinions:
            opinions_by_kol.setdefault(opinion.kol_id, []).append(opinion)

        for entry in promoted_entries:
            calls_for_kol = [call for call in rewritten_trade_calls if call.kol_id == entry.kol_id]
            opinions_for_kol = opinions_by_kol.get(entry.kol_id, [])
            events_for_kol = trade_events_by_kol.get(entry.kol_id, [])
            evidence_items = _build_imported_evidence_items(
                calls_for_kol,
                opinions_for_kol,
                events_for_kol,
            )
            save_json(entry.evidence_path, {"items": evidence_items})
            save_yaml(entry.soul_path, _build_imported_soul(entry, calls_for_kol, events_for_kol))

        refreshed_profiles: list[dict[str, Any]] = []
        for entry in promoted_entries:
            refreshed_profiles.append(refresh_profile(entry.kol_id))

    promoted_summary = {
        "source_dir": core_summary["source_dir"],
        "output_dir": str(data_root),
        "min_signals": min_signals,
        "promoted_count": len(promoted_entries),
        "promoted_kols": [
            {
                "kol_id": entry.kol_id,
                "display_name": entry.display_name,
                "allowed_symbols": entry.allowed_symbols,
            }
            for entry in promoted_entries
        ],
        "rewritten_mock_rows": {
            "trade_calls": len(rewritten_trade_calls),
            "trade_call_events": len(rewritten_trade_events),
            "opinions": len(rewritten_opinions),
        },
        "profiles_refreshed": len(refreshed_profiles),
    }
    save_json_path(
        data_root / "reports" / "imports" / "promoted_kols_summary.json", promoted_summary
    )
    with _data_dir_override(data_root):
        append_jsonl(
            "audit/registry_changes.jsonl",
            {
                "timestamp": _now(),
                "action": "import_promote_kols",
                "promoted_count": len(promoted_entries),
                "kol_ids": [entry.kol_id for entry in promoted_entries],
                "mock_only": True,
            },
        )
    return promoted_summary


def process_pending_imports(
    pending_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    min_signals: int = 1,
) -> dict[str, Any]:
    data_root = (
        Path(output_dir).expanduser().resolve() if output_dir else ensure_runtime_data().resolve()
    )
    pending_root = (
        Path(pending_dir).expanduser().resolve()
        if pending_dir
        else (data_root / "imports" / "pending").resolve()
    )
    pending_root.mkdir(parents=True, exist_ok=True)
    sources = _discover_pending_sources(pending_root)
    summary: dict[str, Any] = {
        "pending_dir": str(pending_root),
        "output_dir": str(data_root),
        "has_new_data": bool(sources),
        "processed_count": 0,
        "deleted_count": 0,
        "processed_sources": [],
        "min_signals": min_signals,
    }
    if not sources:
        save_json_path(data_root / "reports" / "imports" / "pending_imports_summary.json", summary)
        return summary

    for source in sources:
        result = promote_imported_kols(
            source_dir=source.source_dir,
            output_dir=data_root,
            min_signals=min_signals,
        )
        _delete_processed_source(source, pending_root)
        summary["processed_count"] += 1
        summary["deleted_count"] += 1
        summary["processed_sources"].append(
            {
                "source_dir": str(source.source_dir),
                "cleanup_path": str(source.cleanup_path),
                "promoted_count": result["promoted_count"],
                "rewritten_mock_rows": result["rewritten_mock_rows"],
            }
        )

    save_json_path(data_root / "reports" / "imports" / "pending_imports_summary.json", summary)
    return summary


def _load_import_rules() -> ImportRules:
    raw = json.loads(IMPORT_RULES_PATH.read_text(encoding="utf-8"))
    ignored = frozenset(str(entry).strip() for entry in raw.get("ignored_authors", []))
    quote_assets = tuple(str(entry).strip().upper() for entry in raw.get("quote_assets", []))
    raw_mappings = json.loads(AUTHOR_MAPPING_PATH.read_text(encoding="utf-8"))
    author_mappings: dict[str, CanonicalKOLMapping] = {}
    canonical_mappings: dict[str, CanonicalKOLMapping] = {}
    for item in raw_mappings.get("canonical_kols", []):
        mapping = CanonicalKOLMapping(
            display_name=str(item["display_name"]).strip(),
            source_authors=tuple(str(value).strip() for value in item.get("source_authors", [])),
            aliases=tuple(str(value).strip() for value in item.get("aliases", [])),
            kol_id=str(item["kol_id"]).strip() if item.get("kol_id") else None,
        )
        canonical_mappings[_normalize_display_name(mapping.display_name)] = mapping
        for source_author in mapping.source_authors:
            author_mappings[_normalize_display_name(source_author)] = mapping
    return ImportRules(
        ignored_authors=ignored,
        quote_assets=quote_assets,
        author_mappings=author_mappings,
        canonical_mappings=canonical_mappings,
    )


def _resolve_source_csv_dir(source_dir: Path) -> Path:
    root = source_dir.expanduser().resolve()
    if not root.exists():
        raise DomainError(
            f"Import source directory not found: {root}", code="IMPORT_SOURCE_MISSING"
        )
    if _contains_required_csvs(root):
        return root
    nested_dirs = [
        path for path in root.iterdir() if path.is_dir() and _contains_required_csvs(path)
    ]
    if len(nested_dirs) == 1:
        return nested_dirs[0]
    raise DomainError(
        f"Import source directory does not contain the required CSV tables: {root}",
        code="IMPORT_SOURCE_INVALID",
    )


def _discover_pending_sources(pending_root: Path) -> list[PendingImportSource]:
    discovered: list[PendingImportSource] = []
    seen: set[Path] = set()
    if _contains_required_csvs(pending_root):
        discovered.append(PendingImportSource(source_dir=pending_root, cleanup_path=pending_root))
        seen.add(pending_root)
    for child in sorted(path for path in pending_root.iterdir() if path.is_dir()):
        try:
            source_dir = _resolve_source_csv_dir(child)
        except DomainError:
            continue
        if source_dir in seen:
            continue
        discovered.append(PendingImportSource(source_dir=source_dir, cleanup_path=child))
        seen.add(source_dir)
    return discovered


def _contains_required_csvs(path: Path) -> bool:
    return all((path / filename).exists() for filename in _required_csv_filenames())


def _delete_processed_source(source: PendingImportSource, pending_root: Path) -> None:
    cleanup_path = source.cleanup_path
    if cleanup_path == pending_root:
        for filename in _required_csv_filenames():
            file_path = pending_root / filename
            if file_path.exists():
                file_path.unlink()
        return
    if cleanup_path.exists():
        shutil.rmtree(cleanup_path)


def _required_csv_filenames() -> tuple[str, ...]:
    return (
        "kol_trade_calls.csv",
        "trade_call_events.csv",
        "kol_opinions.csv",
        "market_analysis.csv",
        "market_news.csv",
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _canonical_author_name(author_name: str, rules: ImportRules) -> str:
    mapping = rules.author_mappings.get(_normalize_display_name(author_name))
    return mapping.display_name if mapping is not None else author_name


def _build_trade_calls(
    rows: list[dict[str, str]],
    rules: ImportRules,
) -> tuple[list[TradeCall], dict[str, Any]]:
    converted: list[TradeCall] = []
    ignored_authors: list[str] = []
    author_to_kol: dict[str, str] = {}
    dropped_rows = 0
    for row in rows:
        author_name = _clean_text(row.get("author_name"))
        if not author_name or author_name in rules.ignored_authors:
            if author_name:
                ignored_authors.append(author_name)
            dropped_rows += 1
            continue
        canonical_author = _canonical_author_name(author_name, rules)
        trade_id = _required(row, "id")
        symbol = _symbol_from_trading_pair(row.get("trading_pair"), rules.quote_assets)
        entry_zone = _entry_zone(row.get("entry_price_min"), row.get("entry_price_max"))
        notes = _clean_text(row.get("notes"))
        converted.append(
            TradeCall(
                id=str(trade_id),
                evidence_id=f"import_trade_call_{trade_id}",
                kol_id=_candidate_kol_id(canonical_author),
                symbol=symbol,
                side=_normalize_side(row.get("direction")),
                thesis=notes
                or f"{row.get('market_type', 'MARKET')} {row.get('order_type', 'ORDER')} setup",
                status=_normalize_status(row),
                entry_zone=entry_zone,
                invalidation=_decimal_or_empty(row.get("stop_loss")),
                timestamp=_parse_timestamp(_required(row, "created_at")),
                channel_scope=_channel_scope(row.get("channel_id")),
                summary=_trade_call_summary(canonical_author, symbol, row, entry_zone, notes),
                confidence=_trade_call_confidence(row.get("close_reason")),
                outcome_score=_trade_call_outcome(row.get("close_reason")),
            )
        )
        author_to_kol[canonical_author] = converted[-1].kol_id
    return converted, {
        "ignored_authors": ignored_authors,
        "dropped_rows": dropped_rows,
        "author_to_kol": author_to_kol,
    }


def _build_trade_call_events(
    rows: list[dict[str, str]],
    trade_lookup: dict[str, TradeCall],
) -> tuple[list[TradeCallEvent], dict[str, Any]]:
    converted: list[TradeCallEvent] = []
    dropped_rows = 0
    for row in rows:
        trade_call_id = _clean_text(row.get("trade_call_id"))
        if not trade_call_id or trade_call_id not in trade_lookup:
            dropped_rows += 1
            continue
        call = trade_lookup[trade_call_id]
        event_id = _required(row, "id")
        converted.append(
            TradeCallEvent(
                id=str(event_id),
                evidence_id=f"import_trade_event_{event_id}",
                trade_call_id=trade_call_id,
                kol_id=call.kol_id,
                symbol=call.symbol,
                event_type=_normalize_event_type(row.get("event_type")),
                timestamp=_parse_timestamp(_required(row, "effective_at")),
                channel_scope=call.channel_scope,
                summary=_event_summary(call, row),
                confidence=0.74,
            )
        )
    return converted, {"dropped_rows": dropped_rows}


def _build_opinions(
    rows: list[dict[str, str]],
    rules: ImportRules,
) -> tuple[list[KOLOpinion], dict[str, Any]]:
    converted: list[KOLOpinion] = []
    ignored_authors: list[str] = []
    author_to_kol: dict[str, str] = {}
    dropped_rows = 0
    for row in rows:
        author_name = _clean_text(row.get("author_name"))
        summary = _clean_text(row.get("content_summary"))
        if not author_name or author_name in rules.ignored_authors or not summary:
            if author_name and author_name in rules.ignored_authors:
                ignored_authors.append(author_name)
            dropped_rows += 1
            continue
        canonical_author = _canonical_author_name(author_name, rules)
        opinion_id = _required(row, "id")
        converted.append(
            KOLOpinion(
                id=str(opinion_id),
                evidence_id=f"import_opinion_{opinion_id}",
                kol_id=_candidate_kol_id(canonical_author),
                symbol=_symbol_from_text(row.get("mentioned_tokens"), rules.quote_assets) or "BTC",
                sentiment=_normalize_sentiment(row.get("sentiment")),
                timestamp=_parse_timestamp(_required(row, "created_at")),
                channel_scope=_channel_scope(row.get("channel_id")),
                summary=summary,
                confidence=_opinion_confidence(row.get("kol_confidence")),
            )
        )
        author_to_kol[canonical_author] = converted[-1].kol_id
    return converted, {
        "ignored_authors": ignored_authors,
        "dropped_rows": dropped_rows,
        "author_to_kol": author_to_kol,
    }


def _build_market_analyses(
    rows: list[dict[str, str]],
    rules: ImportRules,
) -> tuple[list[KOLOpinion], dict[str, Any]]:
    converted: list[KOLOpinion] = []
    ignored_authors: list[str] = []
    author_to_kol: dict[str, str] = {}
    dropped_rows = 0
    for row in rows:
        author_name = _clean_text(row.get("author_name"))
        summary = _analysis_summary(row)
        if not author_name or author_name in rules.ignored_authors or not summary:
            if author_name and author_name in rules.ignored_authors:
                ignored_authors.append(author_name)
            dropped_rows += 1
            continue
        canonical_author = _canonical_author_name(author_name, rules)
        analysis_id = _required(row, "id")
        converted.append(
            KOLOpinion(
                id=str(analysis_id),
                evidence_id=f"import_market_analysis_{analysis_id}",
                kol_id=_candidate_kol_id(canonical_author),
                symbol=_symbol_from_text(row.get("mentioned_tokens"), rules.quote_assets) or "BTC",
                sentiment=_normalize_sentiment(row.get("sentiment")),
                timestamp=_parse_timestamp(_required(row, "created_at")),
                channel_scope=_channel_scope(row.get("channel_id")),
                summary=summary,
                confidence=_analysis_confidence(row.get("analysis_category")),
            )
        )
        author_to_kol[canonical_author] = converted[-1].kol_id
    return converted, {
        "ignored_authors": ignored_authors,
        "dropped_rows": dropped_rows,
        "author_to_kol": author_to_kol,
    }


def _build_news(rows: list[dict[str, str]]) -> tuple[list[MarketNews], dict[str, Any]]:
    converted: list[MarketNews] = []
    dropped_rows = 0
    for row in rows:
        news_id = _required(row, "id")
        summary = _clean_text(row.get("summary")) or _clean_text(row.get("event_title"))
        if not summary:
            dropped_rows += 1
            continue
        symbol = _symbol_from_text(row.get("mentioned_tokens"), ("USDT", "USD", "USDC", "BUSD"))
        if symbol is None:
            symbol = (
                _symbol_from_text(row.get("event_title"), ("USDT", "USD", "USDC", "BUSD")) or "BTC"
            )
        converted.append(
            MarketNews(
                id=str(news_id),
                evidence_id=f"import_news_{news_id}",
                symbol=symbol,
                importance=_normalize_importance(row.get("impact")),
                timestamp=_parse_timestamp(_required(row, "created_at")),
                channel_scope=_channel_scope(row.get("channel_id")),
                summary=summary,
                confidence=_news_confidence(row.get("source_name"), row.get("source_url")),
            )
        )
    return converted, {"dropped_rows": dropped_rows}


def _analysis_summary(row: dict[str, str]) -> str:
    content = _clean_text(row.get("content_summary"))
    category = _clean_text(row.get("analysis_category")).replace("_", " ").lower()
    timeframe = _clean_text(row.get("timeframe")).replace("_", " ").lower()
    metrics = _metrics_summary(row.get("key_metrics"))
    parts = [content]
    qualifiers = [item for item in [category, timeframe] if item]
    if qualifiers:
        parts.append(f"[{' | '.join(qualifiers)}]")
    if metrics:
        parts.append(f"Key metrics: {metrics}.")
    return " ".join(part for part in parts if part).strip()


def _analysis_confidence(category: str | None) -> float:
    normalized = _clean_text(category).upper()
    if normalized == "TECHNICAL_ANALYSIS":
        return 0.78
    if normalized == "MACRO_ANALYSIS":
        return 0.72
    return 0.69


def _metrics_summary(raw_metrics: str | None) -> str:
    if not raw_metrics:
        return ""
    text = raw_metrics.strip()
    if text in {"{}", ""}:
        return ""
    cleaned = text.strip("{}")
    cleaned = cleaned.replace('"', "")
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    return "; ".join(parts[:4])


def _build_candidate_kols(
    trade_calls: list[TradeCall],
    opinions: list[KOLOpinion],
    market_analyses: list[KOLOpinion],
    author_to_kol: dict[str, str],
) -> list[dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    display_name_by_kol = {kol_id: author for author, kol_id in author_to_kol.items()}
    for call in trade_calls:
        current = metrics.setdefault(
            call.kol_id,
            {
                "kol_id": call.kol_id,
                "display_name": display_name_by_kol.get(call.kol_id, call.kol_id),
                "symbols": set(),
                "trade_calls": 0,
                "opinions": 0,
                "market_analyses": 0,
            },
        )
        current["symbols"].add(call.symbol)
        current["trade_calls"] += 1
    for opinion in opinions:
        current = metrics.setdefault(
            opinion.kol_id,
            {
                "kol_id": opinion.kol_id,
                "display_name": display_name_by_kol.get(opinion.kol_id, opinion.kol_id),
                "symbols": set(),
                "trade_calls": 0,
                "opinions": 0,
                "market_analyses": 0,
            },
        )
        current["symbols"].add(opinion.symbol)
        current["opinions"] += 1
    for analysis in market_analyses:
        current = metrics.setdefault(
            analysis.kol_id,
            {
                "kol_id": analysis.kol_id,
                "display_name": display_name_by_kol.get(analysis.kol_id, analysis.kol_id),
                "symbols": set(),
                "trade_calls": 0,
                "opinions": 0,
                "market_analyses": 0,
            },
        )
        current["symbols"].add(analysis.symbol)
        current["market_analyses"] += 1
    return [
        {
            "kol_id": item["kol_id"],
            "display_name": item["display_name"],
            "symbols": sorted(item["symbols"]),
            "trade_calls": item["trade_calls"],
            "opinions": item["opinions"],
            "market_analyses": item["market_analyses"],
        }
        for item in sorted(metrics.values(), key=lambda entry: entry["kol_id"])
    ]


def _load_registry_from_root(data_root: Path) -> KOLRegistry:
    return KOLRegistry.model_validate(load_json_path(data_root / "registry" / "kols.json"))


def _prune_duplicate_registry_entries(
    entries: list[KOLRegistryEntry],
    *,
    display_name: str,
    canonical_kol_id: str,
    rules: ImportRules,
) -> list[KOLRegistryEntry]:
    mapping = rules.canonical_mappings.get(_normalize_display_name(display_name))
    if mapping is None:
        return entries
    duplicate_names = {
        _normalize_display_name(value)
        for value in [mapping.display_name, *mapping.aliases, *mapping.source_authors]
        if value.strip()
    }
    return [
        entry
        for entry in entries
        if entry.kol_id == canonical_kol_id
        or _normalize_display_name(entry.display_name) not in duplicate_names
    ]


def _resolve_promoted_kol_id(
    display_name: str,
    registry_entries: list[KOLRegistryEntry],
    rules: ImportRules,
) -> str:
    mapped = rules.canonical_mappings.get(_normalize_display_name(display_name))
    normalized = unicodedata.normalize("NFKD", display_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name.strip()).strip("_").lower()
    if not slug:
        slug = hashlib.sha1(display_name.encode("utf-8")).hexdigest()[:10]
    candidate = mapped.kol_id if mapped and mapped.kol_id else f"kol_{slug}"
    for entry in registry_entries:
        if entry.kol_id == candidate or _normalize_display_name(
            entry.display_name
        ) == _normalize_display_name(display_name):
            return entry.kol_id
    return candidate


def _normalize_display_name(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value).lower()


def _build_aliases(display_name: str, rules: ImportRules) -> list[str]:
    aliases = {display_name}
    mapped = rules.canonical_mappings.get(_normalize_display_name(display_name))
    if mapped is not None:
        aliases.update(mapped.aliases)
        aliases.update(mapped.source_authors)
    ascii_name = (
        unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode("ascii")
    )
    if ascii_name and _normalize_display_name(ascii_name) != _normalize_display_name(display_name):
        aliases.add(ascii_name)
    cleaned = re.sub(r"[^\w\s-]+", "", display_name).strip()
    if cleaned and _normalize_display_name(cleaned) != _normalize_display_name(display_name):
        aliases.add(cleaned)
    return sorted(alias for alias in aliases if alias and alias != display_name)


def _rewrite_trade_call(call: TradeCall, id_map: dict[str, str]) -> TradeCall:
    return call.model_copy(update={"kol_id": id_map.get(call.kol_id, call.kol_id)})


def _rewrite_trade_event(event: TradeCallEvent, id_map: dict[str, str]) -> TradeCallEvent:
    return event.model_copy(update={"kol_id": id_map.get(event.kol_id, event.kol_id)})


def _rewrite_opinion(opinion: KOLOpinion, id_map: dict[str, str]) -> KOLOpinion:
    return opinion.model_copy(update={"kol_id": id_map.get(opinion.kol_id, opinion.kol_id)})


def _build_imported_evidence_items(
    trade_calls: list[TradeCall],
    opinions: list[KOLOpinion],
    events: list[TradeCallEvent],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sorted_calls = sorted(trade_calls, key=lambda item: item.timestamp, reverse=True)
    sorted_events = sorted(events, key=lambda item: item.timestamp, reverse=True)
    sorted_opinions = sorted(opinions, key=lambda item: item.timestamp, reverse=True)
    analysis_opinions = [
        item for item in sorted_opinions if item.evidence_id.startswith("import_market_analysis_")
    ]
    regular_opinions = [
        item
        for item in sorted_opinions
        if not item.evidence_id.startswith("import_market_analysis_")
    ]
    for call in sorted_calls[:20]:
        rows.append(
            {
                "evidence_id": call.evidence_id,
                "source_type": "trade_call",
                "source_id": call.id,
                "kol_id": call.kol_id,
                "symbol": call.symbol,
                "timestamp": call.timestamp,
                "channel_scope": call.channel_scope,
                "summary": call.summary,
                "confidence": call.confidence,
            }
        )
    for opinion in regular_opinions[:15]:
        rows.append(
            {
                "evidence_id": opinion.evidence_id,
                "source_type": "opinion",
                "source_id": opinion.id,
                "kol_id": opinion.kol_id,
                "symbol": opinion.symbol,
                "timestamp": opinion.timestamp,
                "channel_scope": opinion.channel_scope,
                "summary": opinion.summary,
                "confidence": opinion.confidence,
            }
        )
    for opinion in analysis_opinions[:10]:
        rows.append(
            {
                "evidence_id": opinion.evidence_id,
                "source_type": "opinion",
                "source_id": opinion.id,
                "kol_id": opinion.kol_id,
                "symbol": opinion.symbol,
                "timestamp": opinion.timestamp,
                "channel_scope": opinion.channel_scope,
                "summary": opinion.summary,
                "confidence": opinion.confidence,
            }
        )
    for event in sorted_events[:20]:
        rows.append(
            {
                "evidence_id": event.evidence_id,
                "source_type": "event",
                "source_id": event.id,
                "kol_id": event.kol_id,
                "symbol": event.symbol,
                "timestamp": event.timestamp,
                "channel_scope": event.channel_scope,
                "summary": event.summary,
                "confidence": event.confidence,
            }
        )
    rows.sort(key=lambda item: item["timestamp"], reverse=True)
    return rows


def _build_imported_soul(
    entry: KOLRegistryEntry,
    trade_calls: list[TradeCall],
    events: list[TradeCallEvent],
) -> dict[str, Any]:
    event_types = {event.event_type for event in events}
    style_traits = ["runtime_only", "imported_history"]
    if "move_to_breakeven" in event_types:
        style_traits.append("move_sl_to_breakeven")
    if "partial_close" in event_types:
        style_traits.append("takes_partial_profit")
    if {call.side for call in trade_calls} == {"long", "short"}:
        style_traits.append("two_way_trader")
    if any(call.status == "closed_loss" for call in trade_calls):
        risk_management = ["explicit_stop_management"]
    else:
        risk_management = ["adaptive_risk_management"]
    soul = KOLSoul(
        kol_id=entry.kol_id,
        identity_boundary=IdentityBoundary(
            must_not_claim_real_identity=True,
            must_state_simulation=True,
        ),
        trading_soul=TradingSoul(
            style_traits=style_traits,
            preferred_setups=["imported_level_based_setups"],
            risk_management=risk_management,
        ),
        reasoning_style=ReasoningStyle(
            summary=f"Imported historical runtime profile for {entry.display_name}.",
            key_patterns=["cite historical evidence", "keep conclusions conditional"],
        ),
        language_soul=LanguageSoul(
            tone="analytical and conditional",
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
    return soul.model_dump(mode="json")


@contextmanager
def _data_dir_override(data_root: Path) -> Iterator[None]:
    previous = os.getenv(DATA_ENV_VAR)
    os.environ[DATA_ENV_VAR] = str(data_root)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(DATA_ENV_VAR, None)
        else:
            os.environ[DATA_ENV_VAR] = previous


def _now() -> datetime:
    return datetime.now(UTC)


def _candidate_kol_id(author_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", author_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name.strip()).strip("_").lower()
    if not slug:
        slug = f"author_{hashlib.sha1(author_name.encode('utf-8')).hexdigest()[:10]}"
    return f"legacy_{slug}"


def _normalize_side(value: str | None) -> str:
    side = _clean_text(value).lower()
    return side if side in {"long", "short"} else "long"


def _normalize_status(row: dict[str, str]) -> str:
    execution = _clean_text(row.get("execution_status")).lower()
    lifecycle = _clean_text(row.get("lifecycle_status")).lower()
    return execution or lifecycle or "open"


def _entry_zone(min_value: str | None, max_value: str | None) -> str:
    minimum = _decimal_or_empty(min_value)
    maximum = _decimal_or_empty(max_value)
    if minimum and maximum and minimum != maximum:
        return f"{minimum}-{maximum}"
    return minimum or maximum or "unknown"


def _trade_call_summary(
    author_name: str,
    symbol: str,
    row: dict[str, str],
    entry_zone: str,
    notes: str,
) -> str:
    direction = _normalize_side(row.get("direction"))
    order_type = (_clean_text(row.get("order_type")) or "order").lower()
    note_text = notes[:180] if notes else "Imported from structured source data."
    return f"{author_name} {direction} {symbol} {order_type} call around {entry_zone}. {note_text}"


def _event_summary(call: TradeCall, row: dict[str, str]) -> str:
    raw_event_type = _clean_text(row.get("event_type")) or "UPDATE"
    payload = _clean_text(row.get("payload"))
    suffix = f" Details: {payload[:180]}" if payload else ""
    return f"{call.kol_id} {call.symbol} event {raw_event_type}.{suffix}".strip()


def _normalize_event_type(value: str | None) -> str:
    raw = _clean_text(value).upper()
    mapping = {
        "CREATED": "created",
        "UPDATED_SL": "update_sl",
        "UPDATED_TPS": "update_tp",
        "MOVED_SL_TO_BE": "move_to_breakeven",
        "CLOSED_PARTIAL": "partial_close",
        "CLOSED_ALL": "full_close",
        "CANCELED": "cancelled",
    }
    return mapping.get(raw, raw.lower())


def _normalize_sentiment(value: str | None) -> str:
    raw = _clean_text(value).upper()
    if raw == "POSITIVE":
        return "bullish"
    if raw == "NEGATIVE":
        return "bearish"
    return "neutral"


def _opinion_confidence(value: str | None) -> float:
    raw = _clean_text(value)
    if not raw:
        return 0.55
    try:
        score = float(raw) / 10.0
    except ValueError:
        return 0.55
    return round(min(max(score, 0.1), 1.0), 2)


def _trade_call_confidence(close_reason: str | None) -> float:
    reason = _clean_text(close_reason).upper()
    if reason == "TP":
        return 0.76
    if reason == "SL":
        return 0.71
    return 0.66


def _trade_call_outcome(close_reason: str | None) -> float | None:
    reason = _clean_text(close_reason).upper()
    if reason == "TP":
        return 0.8
    if reason == "SL":
        return -0.8
    if reason == "MANUAL":
        return 0.1
    if reason == "EXPIRED":
        return -0.1
    return None


def _normalize_importance(value: str | None) -> str:
    impact = _clean_text(value).upper()
    if impact in {"POSITIVE", "NEGATIVE"}:
        return "high"
    if impact == "NEUTRAL":
        return "medium"
    return "low"


def _news_confidence(source_name: str | None, source_url: str | None) -> float:
    if _clean_text(source_name) or _clean_text(source_url):
        return 0.76
    return 0.62


def _symbol_from_trading_pair(value: str | None, quote_assets: tuple[str, ...]) -> str:
    trading_pair = _clean_text(value).upper()
    if not trading_pair:
        return "BTC"
    for suffix in quote_assets:
        if trading_pair.endswith(suffix) and len(trading_pair) > len(suffix):
            return trading_pair[: -len(suffix)]
    return trading_pair


def _symbol_from_text(value: str | None, quote_assets: tuple[str, ...]) -> str | None:
    raw = _clean_text(value).upper()
    if not raw:
        return None
    for token in re.split(r"[^A-Z0-9]+", raw):
        if not token or token in quote_assets:
            continue
        for suffix in quote_assets:
            if token.endswith(suffix) and len(token) > len(suffix):
                return token[: -len(suffix)]
        if 2 <= len(token) <= 10:
            return token
    return None


def _channel_scope(channel_id: str | None) -> str:
    normalized = _clean_text(channel_id)
    return f"imported_channel:{normalized}" if normalized else "imported_channel:unknown"


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if normalized.endswith("+00"):
        normalized = f"{normalized}:00"
    return datetime.fromisoformat(normalized)


def _required(row: dict[str, str], key: str) -> str:
    value = _clean_text(row.get(key))
    if not value:
        raise DomainError(f"Missing required import field: {key}", code="IMPORT_DATA_INVALID")
    return value


def _decimal_or_empty(value: str | None) -> str:
    return _clean_text(value)


def _clean_text(value: str | None) -> str:
    return (value or "").strip()
