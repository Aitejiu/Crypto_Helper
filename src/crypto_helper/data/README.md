# Data Layer Documentation

This document describes the data contracts used by `crypto_helper`.

It covers:

- source batch input formats
- normalization rules
- canonical KOL mapping
- runtime output formats
- pending queue semantics

The goal is to make the import pipeline reproducible and understandable for
other developers.

## Data Layers

The project uses four practical layers.

### 1. Seed layer

Repository-shipped seed files under:

```text
src/crypto_helper/data/
```

Examples:

- `registry/kols.json`
- `kols/<kol_id>/soul.yaml`
- `kols/<kol_id>/profile.json`
- `kols/<kol_id>/evidence.json`
- `mock/*.json`

### 2. Import source layer

Structured external batches containing CSV files.

These are processed either:

- directly via `import core-tables` / `import promote-kols`
- or indirectly through the pending queue

### 3. Normalized mock layer

Runtime normalized JSON files under:

```text
./crypto_helper_data/mock/
```

Files:

- `trade_calls.json`
- `trade_call_events.json`
- `opinions.json`
- `news.json`

### 4. Promoted per-KOL layer

Runtime promoted outputs under:

```text
./crypto_helper_data/
  registry/kols.json
  kols/<kol_id>/soul.yaml
  kols/<kol_id>/profile.json
  kols/<kol_id>/evidence.json
```

## Required Input Batch Files

Each batch must contain these files:

```text
kol_trade_calls.csv
trade_call_events.csv
kol_opinions.csv
market_analysis.csv
market_news.csv
```

Current importer does **not** consume:

- `message_blocks.csv`
- `discord_messages.csv`

## Input File Contracts

### `kol_trade_calls.csv`

Purpose:

- structured trade-call records from a source KOL

Important fields:

- `id`
- `block_id`
- `author_name`
- `channel_id`
- `market_type`
- `trading_pair`
- `direction`
- `order_type`
- `entry_price_min`
- `entry_price_max`
- `stop_loss`
- `notes`
- `created_at`
- `execution_status`
- `lifecycle_status`
- `close_reason`

Importer behavior:

- resolves symbol from `trading_pair`
- normalizes side, status, entry zone, and invalidation
- emits `import_trade_call_<id>`

### `trade_call_events.csv`

Purpose:

- trade lifecycle updates linked to trade calls

Important fields:

- `id`
- `trade_call_id`
- `event_type`
- `source`
- `effective_at`
- `payload`
- `created_at`

Importer behavior:

- maps source event types into runtime event taxonomy
- attaches the event to its normalized trade call
- emits `import_trade_event_<id>`

### `kol_opinions.csv`

Purpose:

- structured KOL market or symbol opinions

Important fields:

- `id`
- `block_id`
- `author_name`
- `content_summary`
- `sentiment`
- `kol_confidence`
- `mentioned_tokens`
- `created_at`
- `channel_id`

Importer behavior:

- normalizes sentiment to `bullish` / `bearish` / `neutral`
- maps confidence into a runtime float
- resolves symbol from `mentioned_tokens`
- emits `import_opinion_<id>`

### `market_analysis.csv`

Purpose:

- structured analytical interpretations associated with a KOL/source

Important fields:

- `id`
- `block_id`
- `author_name`
- `content_summary`
- `analysis_category`
- `key_metrics`
- `mentioned_tokens`
- `sentiment`
- `timeframe`
- `created_at`
- `channel_id`

Importer behavior:

- treated as opinion-like structured evidence
- merged into `mock/opinions.json`
- emits `import_market_analysis_<id>`
- adds category / timeframe / metric context into the summary

### `market_news.csv`

Purpose:

- structured market news or event summaries

Important fields:

- `id`
- `block_id`
- `event_title`
- `summary`
- `event_date`
- `source_name`
- `source_url`
- `impact`
- `mentioned_tokens`
- `created_at`
- `channel_id`

Importer behavior:

- normalizes importance
- resolves symbol from `mentioned_tokens`
- emits `import_news_<id>`

## Processing Pipeline

The importer works in three practical phases.

### Phase 1: Core normalization

Command:

```bash
uv run crypto-helper import core-tables --source-dir /path/to/batch --json
```

What happens:

1. validate required CSV presence
2. read source rows
3. filter ignored authors
4. canonicalize source author names where mapping rules exist
5. normalize symbols, sentiment, status, and event types
6. write normalized runtime mock files
7. emit `core_tables_import_summary.json`

### Phase 2: Canonical KOL mapping

Source authors are normalized through:

- `src/crypto_helper/data/import_configs/core_table_import_rules.json`
- `src/crypto_helper/data/import_configs/kol_author_mappings.json`

This layer is used to:

- ignore low-value or test authors
- merge source aliases into one canonical KOL
- keep stable `kol_id` values for promoted KOLs
- expose query-friendly aliases in the registry

Examples:

- `所长（VIP策略）气运加身` -> `所长`
- `舒琴操作日记VIP分享` -> `舒琴`
- `Owais | Top Tier 👑` -> `Owais`

### Phase 3: KOL promotion

Command:

```bash
uv run crypto-helper import promote-kols --source-dir /path/to/batch --json
```

What happens:

1. run core normalization
2. build candidate KOLs from normalized trade calls, opinions, and market
   analyses
3. promote candidates into real registry entities
4. rewrite mock-layer `kol_id` values to promoted `kol_id`s
5. generate:
   - `registry/kols.json`
   - `kols/<kol_id>/soul.yaml`
   - `kols/<kol_id>/profile.json`
   - `kols/<kol_id>/evidence.json`
6. refresh KOL profiles
7. emit `promoted_kols_summary.json`

## Pending Queue Processing

The scheduled queue is:

```text
./crypto_helper_data/imports/pending/
```

Recommended layout:

```text
./crypto_helper_data/imports/pending/2026-05-08-batch-01/
  kol_trade_calls.csv
  trade_call_events.csv
  kol_opinions.csv
  market_analysis.csv
  market_news.csv
```

Runtime command:

```bash
uv run crypto-helper import process-pending --json
```

Semantics:

1. inspect the pending directory
2. discover complete batch directories
3. if no complete batch exists, return no-op
4. if a batch exists, import it
5. if import succeeds, delete the processed batch directory
6. if import fails, keep the batch directory unchanged

This is the flow used by the recurring `manager-admin` maintenance task.

## Output Files

Successful imports write to:

```text
./crypto_helper_data/
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

## Output Contracts

### `mock/trade_calls.json`

Each item contains:

- `id`
- `evidence_id`
- `kol_id`
- `symbol`
- `side`
- `thesis`
- `status`
- `entry_zone`
- `invalidation`
- `timestamp`
- `channel_scope`
- `summary`
- `confidence`
- `outcome_score`

Example shape:

```json
{
  "id": "575",
  "evidence_id": "import_trade_call_575",
  "kol_id": "kol_trader_gauls",
  "symbol": "BTC",
  "side": "short",
  "status": "closed_loss",
  "entry_zone": "68400.00000000-69500.00000000",
  "timestamp": "2026-02-12T13:40:18.185501Z",
  "channel_scope": "imported_channel:1295135524322934804",
  "summary": "Trader Gauls short BTC limit call around ...",
  "confidence": 0.71
}
```

### `mock/trade_call_events.json`

Each item contains:

- `id`
- `evidence_id`
- `trade_call_id`
- `kol_id`
- `symbol`
- `event_type`
- `timestamp`
- `channel_scope`
- `summary`
- `confidence`

### `mock/opinions.json`

This file contains both:

- normalized `kol_opinions.csv` rows
- normalized `market_analysis.csv` rows

Opinion-derived records use:

- `evidence_id = import_opinion_<id>`

Market-analysis-derived records use:

- `evidence_id = import_market_analysis_<id>`

Common fields:

- `id`
- `evidence_id`
- `kol_id`
- `symbol`
- `sentiment`
- `timestamp`
- `channel_scope`
- `summary`
- `confidence`

### `mock/news.json`

Each item contains:

- `id`
- `evidence_id`
- `symbol`
- `importance`
- `timestamp`
- `channel_scope`
- `summary`
- `confidence`

## Registry Contract

`registry/kols.json` is the canonical runtime registry.

Each entry contains:

- `kol_id`
- `display_name`
- `aliases`
- `status`
- `tier`
- `persona_mode`
- `soul_path`
- `profile_path`
- `evidence_path`
- `allowed_symbols`
- `risk_level`
- `last_updated`

The registry is what typo-tolerant lookup, persona simulation, stats, reports,
and evidence search all resolve against.

## Per-KOL Output Contracts

### `kols/<kol_id>/soul.yaml`

Runtime SOUL for persona simulation.

### `kols/<kol_id>/profile.json`

Runtime KOL profile for persona, stats, and reporting.

Common fields:

- `kol_id`
- `summary`
- `active_symbols`
- `trade_style`
- `reliability`
- `evidence_strength`
- `last_refreshed`
- `limitations`

### `kols/<kol_id>/evidence.json`

Wrapper format:

```json
{
  "items": []
}
```

Each evidence item may come from:

- trade calls
- trade call events
- normalized opinions
- normalized market analysis

Common evidence fields:

- `evidence_id`
- `source_type`
- `source_id`
- `kol_id`
- `symbol`
- `timestamp`
- `channel_scope`
- `summary`
- `confidence`

## Summary Files

### `core_tables_import_summary.json`

Contains:

- source directory
- output directory
- written file counts
- ignored authors
- candidate KOLs
- source / converted / dropped row counts

### `promoted_kols_summary.json`

Contains:

- promoted KOL count
- promoted KOL identities
- rewritten mock row counts
- refreshed profile count

### `pending_imports_summary.json`

Contains:

- whether new data existed
- processed bundle count
- deleted bundle count
- processed source summaries

## Open-Source Safety Notes

For open-source usage, keep these boundaries clear:

- runtime data under `./crypto_helper_data/` should not be committed casually
- raw extracted datasets may contain sensitive provenance and should be handled
  deliberately
- importer outputs are normalized operational data, not a raw private message
  archive
- requests for raw private-message export remain out of scope
