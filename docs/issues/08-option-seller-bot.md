# Issue 8: Implement OptionSellerBot (Grid Volume Farmer) - ✅ COMPLETED

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`
- `docs/issues/14-selection-routing-orchestrator.md`

## Background (reuse existing code)
- Use `GammaMarketClient` for selection and `Polymarket` for order ops.
- Reuse helpers from Issues 4–7.

## Scope
- Add `agents/strategies/option_seller.py` implementing grid logic around mid.

## Tasks
- ✅ Load config; support routed markets via `ops.selected_markets_path` and fallback to `selection.select_markets(cfg)`.
- ✅ Compute mid from orderbook price or `outcomePrices`.
- ✅ Build 3–5 levels per side at 1c spacing; clip sizes from config.
- ✅ Inventory-aware widening and flattening on thresholds (baseline hooks).
- ✅ Refresh quotes on cadence; respect `maker_only`.

## Acceptance Criteria
- ✅ Runs in `dry_run` without network order placement; logs intended actions.
- ✅ No changes to existing modules.
- ✅ Respects per-market EV cap and flatten threshold from config.

## Status
- ✅ Implemented: `agents/strategies/option_seller.py`
- ✅ CLI wired: `run-option-seller`
- ✅ Integrates with refresh/routing workflow (Issues 13 & 14)

## Runbook
```bash
# Recommended: routed workflow
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/option_seller.yaml --limit 20 --fetch-limit 50 --skip-classify
PYTHONPATH=. python3 scripts/python/cli.py route-markets \
  --source-config configs/option_seller.yaml \
  --option-seller-config configs/option_seller.yaml --option-seller-limit 10 --option-seller-output local_state/option_seller/selected_markets.json \
  --market-maker-config configs/market_maker.yaml --market-maker-output local_state/market_maker/selected_markets.json \
  --risk-manager-config configs/risk.yaml --risk-manager-output local_state/risk_manager/selected_markets.json
PYTHONPATH=. python3 scripts/python/cli.py run-option-seller --config configs/option_seller.yaml --duration 60

# Fallback: fresh selection inside the bot
PYTHONPATH=. python3 scripts/python/cli.py run-option-seller --config configs/option_seller.yaml --duration 60
```

## Notes
- Keep logic conservative; no market orders unless flattening (and controlled by config).
