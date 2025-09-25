# Issue 9: Implement MarketMakerBot (inventory-skewed quoting)

## Background (reuse existing code)
- Use `GammaMarketClient` for market discovery; `Polymarket` for orders.
- Reuse helpers from Issues 4–7.

## Scope
- Add `agents/strategies/market_maker.py` with inventory-skewed mid and laddered quotes.

### Integration with selection/refresh
- Use `agents/strategies/selection.select_markets(cfg)` for fresh selection, or
  `select_markets_from_cache(cfg)` after a refresh has populated `local_db_markets/markets.json`.
- Refresh the cache and Chroma via CLI before bot start if relying on cache.
  - See issue 13 for details.

## Tasks
- Select 5–8 high-volume markets.
- Compute mid and apply skew: `mid_skew = mid + k*(inventory/limit)`.
- Ladder 2–4 levels per side; increase size deeper.
- Pull/widen on volatility; reduce size on one-way flow.
- Integrate selection: honor `market_selection.min_volume_24h`, `max_spread_cents`, `mid_price_band`.
- Add config flags support: `market_selection.limit`, `fetch_limit`, `classify`.
- Optionally use cached selection (after running refresh) for faster startup.

## Acceptance Criteria
- `dry_run` works without order placement.
- Honors per-market EV cap and maker-only quoting.
- Clean logs show skew, levels, and actions.
- If using cache path, a documented `refresh-markets` run precedes bot start.

## Notes
- Keep parameters from config; no hardcoded values.
- Selection/refresh references:
  - CLI (run prior to cached selection):
    ```bash
    PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/market_maker.yaml \
      --limit 8 --fetch-limit 20 --skip-classify
    ```
  - Config knobs in `market_selection`:
    - `limit`, `fetch_limit`, `classify`, `min_volume_24h`, `max_spread_cents`, `mid_price_band`.
  - Output destinations (optional in `ops`): `markets_json_path`, `markets_chroma_dir`.

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`
- `docs/issues/14-selection-routing-orchestrator.md`
