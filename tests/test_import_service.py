from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from crypto_helper.cli import app
from crypto_helper.core.import_service import (
    import_core_tables,
    process_pending_imports,
    promote_imported_kols,
)


def test_import_core_tables_builds_mock_files(tmp_path: Path) -> None:
    source_dir = _build_source_dir(tmp_path / "source")
    output_dir = tmp_path / "output"

    summary = import_core_tables(source_dir=source_dir, output_dir=output_dir)

    assert summary["files_written"]["mock/trade_calls.json"] == 1
    assert summary["files_written"]["mock/trade_call_events.json"] == 2
    assert summary["files_written"]["mock/opinions.json"] == 2
    assert summary["files_written"]["mock/news.json"] == 1

    trade_calls = json.loads((output_dir / "mock" / "trade_calls.json").read_text(encoding="utf-8"))
    trade_events = json.loads(
        (output_dir / "mock" / "trade_call_events.json").read_text(encoding="utf-8")
    )
    opinions = json.loads((output_dir / "mock" / "opinions.json").read_text(encoding="utf-8"))
    news = json.loads((output_dir / "mock" / "news.json").read_text(encoding="utf-8"))

    assert trade_calls[0]["kol_id"].startswith("legacy_")
    assert trade_calls[0]["symbol"] == "BTC"
    assert trade_events[0]["event_type"] == "created"
    assert opinions[0]["sentiment"] == "bullish"
    assert any(item["evidence_id"].startswith("import_market_analysis_") for item in opinions)
    assert news[0]["importance"] == "high"
    assert summary["converted_rows"]["market_analyses"] == 1


def test_import_core_tables_cli_returns_json(cli_runner: CliRunner, tmp_path: Path) -> None:
    source_dir = _build_source_dir(tmp_path / "source")
    output_dir = tmp_path / "output"

    result = cli_runner.invoke(
        app,
        [
            "import",
            "core-tables",
            "--source-dir",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["files_written"]["mock/trade_calls.json"] == 1


def test_promote_imported_kols_creates_registry_entries(tmp_path: Path) -> None:
    source_dir = _build_source_dir(tmp_path / "source")
    output_dir = _build_runtime_dir(tmp_path / "runtime")

    summary = promote_imported_kols(source_dir=source_dir, output_dir=output_dir, min_signals=1)

    assert summary["promoted_count"] == 1
    registry = json.loads((output_dir / "registry" / "kols.json").read_text(encoding="utf-8"))
    promoted = [entry for entry in registry["kols"] if entry["display_name"] == "BTC Master"]
    assert promoted
    promoted_kol_id = promoted[0]["kol_id"]
    trade_calls = json.loads((output_dir / "mock" / "trade_calls.json").read_text(encoding="utf-8"))
    evidence = json.loads(
        (output_dir / "kols" / promoted_kol_id / "evidence.json").read_text(encoding="utf-8")
    )
    assert trade_calls[0]["kol_id"] == promoted_kol_id
    assert (output_dir / "kols" / promoted_kol_id / "soul.yaml").exists()
    assert (output_dir / "kols" / promoted_kol_id / "profile.json").exists()
    assert (output_dir / "kols" / promoted_kol_id / "evidence.json").exists()
    assert any(
        item["evidence_id"].startswith("import_market_analysis_") for item in evidence["items"]
    )


def test_promote_imported_kols_cli_returns_json(cli_runner: CliRunner, tmp_path: Path) -> None:
    source_dir = _build_source_dir(tmp_path / "source")
    output_dir = _build_runtime_dir(tmp_path / "runtime")

    result = cli_runner.invoke(
        app,
        [
            "import",
            "promote-kols",
            "--source-dir",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["promoted_count"] == 1


def test_process_pending_imports_cli_returns_json(cli_runner: CliRunner, tmp_path: Path) -> None:
    output_dir = _build_runtime_dir(tmp_path / "runtime")
    pending_dir = tmp_path / "pending"
    source_dir = _build_source_dir(tmp_path / "source")
    bundle_dir = pending_dir / "bundle-1"
    shutil.copytree(source_dir, bundle_dir)

    result = cli_runner.invoke(
        app,
        [
            "import",
            "process-pending",
            "--pending-dir",
            str(pending_dir),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["processed_count"] == 1


def test_process_pending_imports_skips_when_no_new_data(tmp_path: Path) -> None:
    output_dir = _build_runtime_dir(tmp_path / "runtime")
    pending_dir = tmp_path / "pending"

    summary = process_pending_imports(pending_dir=pending_dir, output_dir=output_dir, min_signals=1)

    assert summary["has_new_data"] is False
    assert summary["processed_count"] == 0
    assert pending_dir.exists()


def test_process_pending_imports_consumes_bundle_directory(tmp_path: Path) -> None:
    output_dir = _build_runtime_dir(tmp_path / "runtime")
    pending_dir = tmp_path / "pending"
    source_dir = _build_source_dir(tmp_path / "source")
    bundle_dir = pending_dir / "bundle-1"
    shutil.copytree(source_dir, bundle_dir)

    summary = process_pending_imports(pending_dir=pending_dir, output_dir=output_dir, min_signals=1)

    assert summary["has_new_data"] is True
    assert summary["processed_count"] == 1
    assert summary["deleted_count"] == 1
    assert not bundle_dir.exists()


def test_promote_imported_kols_applies_manual_author_mapping(tmp_path: Path) -> None:
    source_dir = _build_source_dir(tmp_path / "source")
    _rewrite_csv_rows(
        source_dir / "kol_trade_calls.csv",
        lambda row: {**row, "author_name": "Owais | Top Tier 👑"},
    )
    _rewrite_csv_rows(
        source_dir / "kol_opinions.csv",
        lambda row: {**row, "author_name": "Owais"},
    )
    _rewrite_csv_rows(
        source_dir / "market_analysis.csv",
        lambda row: {**row, "author_name": "Owais | Top Tier 👑"},
    )
    output_dir = _build_runtime_dir(tmp_path / "runtime")

    summary = promote_imported_kols(source_dir=source_dir, output_dir=output_dir, min_signals=1)

    assert summary["promoted_count"] == 1
    registry = json.loads((output_dir / "registry" / "kols.json").read_text(encoding="utf-8"))
    promoted = [entry for entry in registry["kols"] if entry["display_name"] == "Owais"]
    assert promoted
    assert "Owais | Top Tier 👑" in promoted[0]["aliases"]


def _build_source_dir(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        base_dir / "kol_trade_calls.csv",
        [
            "id",
            "block_id",
            "author_name",
            "channel_id",
            "market_type",
            "trading_pair",
            "direction",
            "order_type",
            "entry_price_min",
            "entry_price_max",
            "target_prices",
            "stop_loss",
            "leverage",
            "timeframe",
            "notes",
            "created_at",
            "updated_at",
            "lifecycle_status",
            "execution_status",
            "close_reason",
            "entry_filled_at",
            "filled_entry_price",
            "closed_at",
            "closed_price",
            "remaining_position_pct",
        ],
        [
            {
                "id": "1",
                "block_id": "11",
                "author_name": "BTC Master",
                "channel_id": "chan-1",
                "market_type": "FUTURES",
                "trading_pair": "BTCUSDT",
                "direction": "LONG",
                "order_type": "LIMIT",
                "entry_price_min": "62000",
                "entry_price_max": "62300",
                "target_prices": "63000",
                "stop_loss": "61500",
                "leverage": "",
                "timeframe": "DAY_TRADE",
                "notes": "Wait for reclaim.",
                "created_at": "2026-02-01 10:00:00+00",
                "updated_at": "2026-02-01 11:00:00+00",
                "lifecycle_status": "CLOSED",
                "execution_status": "CLOSED",
                "close_reason": "TP",
                "entry_filled_at": "",
                "filled_entry_price": "",
                "closed_at": "",
                "closed_price": "",
                "remaining_position_pct": "0",
            },
            {
                "id": "2",
                "block_id": "12",
                "author_name": "qa-bot",
                "channel_id": "chan-2",
                "market_type": "FUTURES",
                "trading_pair": "ETHUSDT",
                "direction": "SHORT",
                "order_type": "LIMIT",
                "entry_price_min": "3000",
                "entry_price_max": "3010",
                "target_prices": "2900",
                "stop_loss": "3050",
                "leverage": "",
                "timeframe": "DAY_TRADE",
                "notes": "ignore row",
                "created_at": "2026-02-01 10:00:00+00",
                "updated_at": "2026-02-01 11:00:00+00",
                "lifecycle_status": "OPEN",
                "execution_status": "OPEN",
                "close_reason": "",
                "entry_filled_at": "",
                "filled_entry_price": "",
                "closed_at": "",
                "closed_price": "",
                "remaining_position_pct": "1",
            },
        ],
    )
    _write_csv(
        base_dir / "trade_call_events.csv",
        [
            "id",
            "trade_call_id",
            "event_type",
            "source",
            "source_block_id",
            "source_message_id",
            "effective_at",
            "payload",
            "dedup_key",
            "created_at",
        ],
        [
            {
                "id": "101",
                "trade_call_id": "1",
                "event_type": "CREATED",
                "source": "KOL_MESSAGE",
                "source_block_id": "11",
                "source_message_id": "",
                "effective_at": "2026-02-01 10:00:00+00",
                "payload": "entry created",
                "dedup_key": "",
                "created_at": "2026-02-01 10:00:00+00",
            },
            {
                "id": "102",
                "trade_call_id": "1",
                "event_type": "UPDATED_SL",
                "source": "KOL_MESSAGE",
                "source_block_id": "11",
                "source_message_id": "",
                "effective_at": "2026-02-01 10:30:00+00",
                "payload": "stop tightened",
                "dedup_key": "",
                "created_at": "2026-02-01 10:30:00+00",
            },
        ],
    )
    _write_csv(
        base_dir / "kol_opinions.csv",
        [
            "id",
            "block_id",
            "author_name",
            "content_summary",
            "sentiment",
            "kol_confidence",
            "mentioned_tokens",
            "created_at",
            "channel_id",
        ],
        [
            {
                "id": "201",
                "block_id": "21",
                "author_name": "BTC Master",
                "content_summary": "BTC reclaim improves odds of continuation.",
                "sentiment": "POSITIVE",
                "kol_confidence": "8",
                "mentioned_tokens": "BTC",
                "created_at": "2026-02-01 09:00:00+00",
                "channel_id": "chan-1",
            }
        ],
    )
    _write_csv(
        base_dir / "market_analysis.csv",
        [
            "id",
            "block_id",
            "author_name",
            "content_summary",
            "analysis_category",
            "key_metrics",
            "mentioned_tokens",
            "sentiment",
            "timeframe",
            "created_at",
            "channel_id",
        ],
        [
            {
                "id": "251",
                "block_id": "22",
                "author_name": "BTC Master",
                "content_summary": (
                    "BTC remains in a reaction zone until reclaim confirms continuation."
                ),
                "analysis_category": "TECHNICAL_ANALYSIS",
                "key_metrics": '{"Reaction zone","Reclaim confirmation"}',
                "mentioned_tokens": "{BTC}",
                "sentiment": "POSITIVE",
                "timeframe": "DAY_TRADE",
                "created_at": "2026-02-01 09:30:00+00",
                "channel_id": "chan-1",
            }
        ],
    )
    _write_csv(
        base_dir / "market_news.csv",
        [
            "id",
            "block_id",
            "event_title",
            "summary",
            "event_date",
            "source_name",
            "source_url",
            "shared_by_author",
            "impact",
            "mentioned_tokens",
            "created_at",
            "channel_id",
        ],
        [
            {
                "id": "301",
                "block_id": "31",
                "event_title": "US jobs miss expectations",
                "summary": "Macro release increases BTC volatility expectations.",
                "event_date": "2026-02-01 08:00:00+00",
                "source_name": "Macro Wire",
                "source_url": "https://example.com/news/1",
                "shared_by_author": "",
                "impact": "NEGATIVE",
                "mentioned_tokens": "BTC",
                "created_at": "2026-02-01 08:01:00+00",
                "channel_id": "chan-news",
            }
        ],
    )
    return base_dir


def _build_runtime_dir(base_dir: Path) -> Path:
    (base_dir / "registry").mkdir(parents=True, exist_ok=True)
    (base_dir / "mock").mkdir(parents=True, exist_ok=True)
    (base_dir / "kols").mkdir(parents=True, exist_ok=True)
    (base_dir / "audit").mkdir(parents=True, exist_ok=True)
    (base_dir / "reports" / "imports").mkdir(parents=True, exist_ok=True)
    registry = {
        "kols": [
            {
                "kol_id": "kol_a",
                "display_name": "KOL_A",
                "aliases": ["AlphaTrend", "A"],
                "status": "active",
                "tier": "core",
                "persona_mode": "dedicated_or_runtime",
                "soul_path": "kols/kol_a/soul.yaml",
                "profile_path": "kols/kol_a/profile.json",
                "evidence_path": "kols/kol_a/evidence.json",
                "allowed_symbols": ["BTC", "ETH"],
                "risk_level": "medium",
                "last_updated": "2026-05-06T12:00:00+00:00",
            }
        ]
    }
    (base_dir / "registry" / "kols.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (base_dir / "kols" / "kol_a").mkdir(parents=True, exist_ok=True)
    (base_dir / "kols" / "kol_a" / "profile.json").write_text(
        json.dumps(
            {
                "kol_id": "kol_a",
                "summary": "seed",
                "active_symbols": ["BTC"],
                "trade_style": ["seed"],
                "reliability": 0.5,
                "evidence_strength": 1,
                "last_refreshed": "2026-05-06T12:00:00+00:00",
                "limitations": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (base_dir / "kols" / "kol_a" / "evidence.json").write_text(
        json.dumps({"items": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (base_dir / "kols" / "kol_a" / "soul.yaml").write_text(
        "\n".join(
            [
                "kol_id: kol_a",
                "identity_boundary:",
                "  must_not_claim_real_identity: true",
                "  must_state_simulation: true",
                "trading_soul:",
                "  style_traits: [seed]",
                "  preferred_setups: [seed]",
                "  risk_management: [seed]",
                "reasoning_style:",
                "  summary: seed",
                "  key_patterns: [seed]",
                "language_soul:",
                "  tone: seed",
                "  disclaimers:",
                "    - 这是基于历史画像的模拟推理，不代表该 KOL 本人实时观点。",
                "safety_rules:",
                "  no_direct_financial_advice: true",
                "  must_include_evidence: true",
                "  must_include_confidence: true",
                "  must_include_limitations: true",
                "update_policy:",
                "  auto_apply_threshold: 0.8",
                "  manual_review_threshold: 0.6",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return base_dir


def _rewrite_csv_rows(
    path: Path,
    transform: Callable[[dict[str, str]], dict[str, str]],
) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [transform(row) for row in reader]
        fieldnames = list(reader.fieldnames or [])
    _write_csv(path, fieldnames, rows)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
