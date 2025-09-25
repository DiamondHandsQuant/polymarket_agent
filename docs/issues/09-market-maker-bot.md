# Issue 9: Implement MarketMakerBot (inventory-skewed quoting) - ✅ COMPLETED

## Background (reuse existing code)
- Use `GammaMarketClient` for market discovery; `Polymarket` for orders.
- Reuse helpers from Issues 4–7.

## Scope
- Add `agents/strategies/market_maker.py` with inventory-skewed mid and laddered quotes.

### Integration with selection
- Use `agents/strategies/selection.select_markets(cfg)` for fresh selection (no cache/routed inputs).

## Tasks
- ✅ Use `selection.select_markets(cfg)` honoring YAML `limit` (e.g., 5–8) and `min_volume_24h`.
- ✅ Compute mid and apply skew: `mid_skew = mid + k*(inventory/limit)`.
- ✅ Ladder 2–4 levels per side; increase size deeper.
- ✅ Pull/widen on volatility; reduce size on one-way flow.
- ✅ Integrate selection: honor `market_selection.min_volume_24h`, `max_spread_cents`, `mid_price_band`.
- ✅ Add config flags support: `market_selection.limit`, `fetch_limit`, `classify`.
- ✅ Support routed market selection via `ops.selected_markets_path`.
 

## Acceptance Criteria
- ✅ `dry_run` works without order placement.
- ✅ Honors per-market EV cap and maker-only quoting.
- ✅ Clean logs show skew, levels, and actions.
- ✅ If using cache path, a documented `refresh-markets` run precedes bot start.
- ✅ Bot supports both routed selections and fresh market selection.

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

### Status
- ✅ **COMPLETED** - Market Maker bot fully implemented and tested.
- ✅ Selection/refresh and routing flow are implemented (see Issues 13 and 14).
- ✅ Market Maker bot supports both routed selections (`ops.selected_markets_path`) and fresh selection (`selection.select_markets(cfg)`).
- ✅ Inventory-skewed quoting with configurable parameters implemented.
- ✅ Grid building, order placement, and dry-run functionality working.
- ✅ Configs allow low-volume testing; adjust thresholds in YAML for production.

### Runbook (completed implementation)
```bash
# Option 1: Use routed markets (recommended workflow)
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/market_maker.yaml --limit 20 --fetch-limit 50 --skip-classify
PYTHONPATH=. python3 scripts/python/cli.py route-markets --source-config configs/market_maker.yaml --market-maker-config configs/market_maker.yaml --market-maker-limit 5 --market-maker-output local_state/market_maker/selected_markets.json --option-seller-config configs/option_seller.yaml --option-seller-limit 10 --option-seller-output local_state/option_seller/selected_markets.json --risk-manager-config configs/risk.yaml --risk-manager-limit 15 --risk-manager-output local_state/risk_manager/selected_markets.json
PYTHONPATH=. python3 scripts/python/cli.py run-market-maker --config configs/market_maker.yaml --duration 60

# Option 2: Fresh selection (fallback if no routed path configured)
PYTHONPATH=. python3 scripts/python/cli.py run-market-maker --config configs/market_maker.yaml --duration 60
```

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`
- `docs/issues/14-selection-routing-orchestrator.md`
