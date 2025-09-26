## Market selection, refresh workflow, and cache/Chroma persistence - ✅ COMPLETED

### Summary
- Implemented a systematic market selection and refresh flow.
- Added a CLI command to refresh the local markets cache and Chroma index.
- Introduced configuration flags for selection behavior and fetch sizing.
- Decoupled/demo code removed from CLI to avoid ad‑hoc persistence.

### Scope
- Files: `agents/strategies/selection.py`, `agents/connectors/chroma.py`, `scripts/python/cli.py`
- Config: `configs/*` may opt into new flags under `market_selection` and `ops`.

### Key Changes
- Selection
  - `selection.select_markets(cfg)` now supports:
    - `market_selection.limit`: cap on returned markets.
    - `market_selection.fetch_limit`: cap on fetch size from the provider.
    - `market_selection.classify` (bool): toggle LLM classification; when false, skips LLM and cache writes.
  - Filter logic unchanged, but respects updated `min_volume_24h`, `max_spread_cents`, `mid_price_band`.

- Persistence
  - `chroma.persist_markets(markets, json_file_path, vector_db_directory)` writes JSON and updates Chroma.
  - Handles empty results gracefully (no Chroma build when empty).

- CLI
  - New: `refresh-markets` command
    - Flags:
      - `--config`: path to YAML
      - `--limit`, `--fetch-limit`: override selection sizes
      - `--min-volume-24h`: override volume threshold for this run
      - `--skip-classify`: disable LLM classification for speed
      - `--markets-json-path`, `--markets-chroma-dir`: output destinations (can be set in config `ops` as well)
    - Flow: read config → apply CLI overrides → call `selection.select_markets` → persist via `chroma.persist_markets`.

- CLI cleanup
  - Removed demo `run_autonomous_trader` command and its dependency on `agents/application/trade.py`.

### Usage
```bash
# Basic refresh using config values
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/option_seller.yaml

# Fast refresh for 20 markets without classification
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/option_seller.yaml \
  --limit 20 --fetch-limit 20 --skip-classify

# Temporarily relax volume threshold
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/option_seller.yaml \
  --min-volume-24h 0
```

### Config knobs
- In `market_selection`:
  - `limit`: int
  - `fetch_limit`: int
  - `classify`: bool
  - `min_volume_24h`, `max_spread_cents`, `mid_price_band`, `exclude_tags`
- In `ops` (optional, for destinations):
  - `markets_json_path`
  - `markets_chroma_dir`

### Migration notes
- If a strategy consumes cached markets (e.g., `select_markets_from_cache`), run `refresh-markets` before starting the bot to avoid stale/empty data.
- For faster iterations, disable classification via `market_selection.classify: false` or `--skip-classify`.

### Status
- ✅ Implemented `refresh-markets` CLI and `persist_markets` in Chroma connector
- ✅ Config-driven selection and persistence; demo path removed
- ✅ Integrated with orchestrator (Issue 14)

### Follow-ups
- Add periodic auto-refresh task (cron) with backoff and TTL guard.
- Optional: write a small health log line with selected count and reasons for rejections.
- Optional: add tag-based filtering.

### See also
- `docs/issues/04-market-selection-helper.md`
- `docs/issues/08-option-seller-bot.md`
- `docs/issues/14-selection-routing-orchestrator.md`

