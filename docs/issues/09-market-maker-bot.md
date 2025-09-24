# Issue 9: Implement MarketMakerBot (inventory-skewed quoting)

## Background (reuse existing code)
- Use `GammaMarketClient` for market discovery; `Polymarket` for orders.
- Reuse helpers from Issues 4–7.

## Scope
- Add `agents/strategies/market_maker.py` with inventory-skewed mid and laddered quotes.

## Tasks
- Select 5–8 high-volume markets.
- Compute mid and apply skew: `mid_skew = mid + k*(inventory/limit)`.
- Ladder 2–4 levels per side; increase size deeper.
- Pull/widen on volatility; reduce size on one-way flow.

## Acceptance Criteria
- `dry_run` works without order placement.
- Honors per-market EV cap and maker-only quoting.
- Clean logs show skew, levels, and actions.

## Notes
- Keep parameters from config; no hardcoded values.
