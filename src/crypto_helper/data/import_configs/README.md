# crypto_helper Import Queue README

This document defines the import semantics for structured KOL data and the
runtime data formats produced by the importer layer.

## Scope

This README covers:

- pending import queue layout
- recurring processing semantics
- successful import cleanup rules
- normalized mock-layer output
- promoted KOL output
- mapping/config files used by the importer

The implementation entrypoints are:

- `uv run crypto-helper import core-tables --source-dir <dir> --json`
- `uv run crypto-helper import promote-kols --source-dir <dir> --json`
- `uv run crypto-helper import process-pending --json`

## Source Files Required Per Batch

Each import batch must contain these files:

```text
kol_trade_calls.csv
trade_call_events.csv
kol_opinions.csv
market_analysis.csv
market_news.csv
```

`message_blocks.csv` and `discord_messages.csv` are not consumed by the current
importer.

## Pending Queue Layout

The recurring queue is:

```text
<repo>/crypto_helper_data/imports/pending/
```

Preferred layout is one batch per subdirectory:

```text
<repo>/crypto_helper_data/imports/pending/2026-05-08-batch-01/
  kol_trade_calls.csv
  trade_call_events.csv
  kol_opinions.csv
  market_analysis.csv
  market_news.csv
```

This is preferred over dropping files directly into `pending/` because:

- each batch is isolated
- cleanup is unambiguous
- failed batches are easier to inspect
- repeated imports are easier to reason about

## Recurring Processing Semantics

The scheduled maintenance command is:

```bash
uv run crypto-helper import process-pending --json
```

Default behavior:

1. Check `<repo>/crypto_helper_data/imports/pending/`
2. Discover subdirectories that contain one complete import batch
3. If no complete batch exists, return a no-op JSON result
4. If one or more complete batches exist, process them one by one
5. For each successful batch:
   - run the full promotion pipeline
   - update runtime mock data
   - update registry and per-KOL files
   - delete the processed batch directory
6. If a batch fails:
   - do not delete it
   - leave it in `pending/` for retry or inspection

No-op example:

```json
{
  "pending_dir": "/home/zhmao/crypto_helper/crypto_helper_data/imports/pending",
  "output_dir": "/home/zhmao/crypto_helper/crypto_helper_data",
  "has_new_data": false,
  "processed_count": 0,
  "deleted_count": 0,
  "processed_sources": [],
  "min_signals": 1,
  "ok": true
}
```

## Cleanup Rules

Cleanup happens only after a successful import.

Preferred case:

- input is a batch subdirectory under `pending/`
- importer deletes that whole subdirectory after success

Fallback case:

- input files are placed directly in `pending/`
- importer deletes only the required CSV files after success

Failure case:

- nothing is deleted

## Mapping and Normalization Config

Importer behavior is controlled by:

```text
src/crypto_helper/data/import_configs/core_table_import_rules.json
src/crypto_helper/data/import_configs/kol_author_mappings.json
```

### core_table_import_rules.json

Used for:

- ignored source authors
- quote assets for symbol normalization

### kol_author_mappings.json

Used for:

- canonical KOL display names
- source author aliases
- stable `kol_id` overrides
- merged registry identities

Example mapping intent:

- `所长（VIP策略）气运加身` -> `所长`
- `舒琴操作日记VIP分享` -> `舒琴`
- `Owais | Top Tier 👑` -> `Owais`

## Processed Output Layout

Successful imports write to the runtime data root:

```text
<repo>/crypto_helper_data/
```

Main outputs:

```text
registry/kols.json

mock/trade_calls.json
mock/trade_call_events.json
mock/opinions.json
mock/news.json

kols/<kol_id>/soul.yaml
kols/<kol_id>/profile.json
kols/<kol_id>/evidence.json

reports/imports/core_tables_import_summary.json
reports/imports/promoted_kols_summary.json
reports/imports/pending_imports_summary.json
```

## Mock Output Formats

### mock/trade_calls.json

Array of normalized trade call records.

Key fields:

```json
{
  "id": "575",
  "evidence_id": "import_trade_call_575",
  "kol_id": "kol_trader_gauls",
  "symbol": "BTC",
  "side": "short",
  "status": "closed_loss",
  "timestamp": "2026-02-12T13:40:18.185501Z",
  "channel_scope": "imported_channel:1295135524322934804",
  "summary": "Trader Gauls short BTC limit call around 68400.00000000-69500.00000000. ...",
  "confidence": 0.71
}
```

### mock/trade_call_events.json

Array of normalized trade lifecycle events.

Key fields:

```json
{
  "id": "1972",
  "evidence_id": "import_trade_event_1972",
  "trade_call_id": "575",
  "kol_id": "kol_trader_gauls",
  "symbol": "BTC",
  "event_type": "full_close",
  "timestamp": "2026-02-14T11:21:59.999000Z",
  "channel_scope": "imported_channel:1295135524322934804",
  "summary": "kol_trader_gauls BTC event SL_HIT. Details: ...",
  "confidence": 0.74
}
```

### mock/opinions.json

Array containing both:

- normalized `kol_opinions.csv` rows
- normalized `market_analysis.csv` rows

`market_analysis.csv` is merged into this file, not written separately.

Opinion-style rows use:

```json
{
  "id": "201",
  "evidence_id": "import_opinion_201",
  "kol_id": "kol_xxx",
  "symbol": "BTC",
  "sentiment": "bullish",
  "timestamp": "2026-02-01T09:00:00Z",
  "channel_scope": "imported_channel:chan-1",
  "summary": "BTC reclaim improves odds of continuation.",
  "confidence": 0.8
}
```

Market-analysis-derived rows use:

```json
{
  "id": "264",
  "evidence_id": "import_market_analysis_264",
  "kol_id": "kol_trader_gauls",
  "symbol": "BTC",
  "sentiment": "neutral",
  "timestamp": "2026-02-16T18:19:15.718493Z",
  "channel_scope": "imported_channel:unknown",
  "summary": "BTC ... [technical analysis | swing] Key metrics: ...",
  "confidence": 0.78
}
```

### mock/news.json

Array of normalized market news items.

Key fields:

```json
{
  "id": "301",
  "evidence_id": "import_news_301",
  "symbol": "BTC",
  "importance": "high",
  "timestamp": "2026-02-01T08:01:00Z",
  "channel_scope": "imported_channel:chan-news",
  "summary": "Macro release increases BTC volatility expectations.",
  "confidence": 0.78
}
```

## Registry Output Format

`registry/kols.json` is the promoted KOL registry used by lookup, persona,
report, and stats flows.

Each entry contains:

```json
{
  "kol_id": "kol_suozhang",
  "display_name": "所长",
  "aliases": ["所长（VIP策略）气运加身"],
  "status": "active",
  "tier": "dynamic",
  "persona_mode": "runtime_only",
  "soul_path": "kols/kol_suozhang/soul.yaml",
  "profile_path": "kols/kol_suozhang/profile.json",
  "evidence_path": "kols/kol_suozhang/evidence.json",
  "allowed_symbols": ["BTC", "ETH", "SOL"],
  "risk_level": "unknown",
  "last_updated": "2026-05-07T16:40:28.705821Z"
}
```

## Per-KOL Output Format

### kols/<kol_id>/soul.yaml

Generated runtime SOUL used by persona simulation.

### kols/<kol_id>/profile.json

Generated profile used by stats/report/persona services.

Common fields:

```json
{
  "kol_id": "kol_trader_gauls",
  "summary": "...",
  "active_symbols": ["BTC", "ETH"],
  "trade_style": ["move_sl_to_breakeven"],
  "reliability": 0.43,
  "evidence_strength": 5,
  "last_refreshed": "2026-05-07T16:40:28.000000Z",
  "limitations": []
}
```

### kols/<kol_id>/evidence.json

Array wrapper:

```json
{
  "items": [...]
}
```

Evidence items are drawn from:

- trade calls
- trade call events
- normalized opinions
- normalized market analysis

Common fields:

```json
{
  "evidence_id": "import_market_analysis_264",
  "source_type": "opinion",
  "source_id": "264",
  "kol_id": "kol_trader_gauls",
  "symbol": "BTC",
  "timestamp": "2026-02-16T18:19:15.718493Z",
  "channel_scope": "imported_channel:unknown",
  "summary": "BTC ... [technical analysis | swing]",
  "confidence": 0.78
}
```

## Summary Files

### core_tables_import_summary.json

Describes one normalization run:

- source rows
- converted rows
- dropped rows
- candidate KOL list

### promoted_kols_summary.json

Describes one promotion run:

- promoted KOLs
- rewritten mock row counts
- refreshed profile count

### pending_imports_summary.json

Describes one queue-processing run:

- whether new data existed
- how many batches were processed
- how many batches were deleted
- per-batch import results

## Operational Contract

When adding new source data:

1. Create a new batch directory under `<repo>/crypto_helper_data/imports/pending/`
2. Copy the five required CSV files into that directory
3. Wait for the recurring `manager-admin` cron run, or run:

```bash
uv run crypto-helper import process-pending --json
```

4. Confirm:
   - `has_new_data: true`
   - `processed_count > 0`
   - batch directory was deleted
   - runtime registry/mock outputs were refreshed

Do not overwrite old processed runtime data by hand.
Use the importer pipeline so normalization, mapping, promotion, cleanup, and
audit behavior stay consistent.
