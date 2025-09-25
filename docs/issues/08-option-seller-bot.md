# Issue 8: Implement OptionSellerBot (Grid Volume Farmer)

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`

## Background (reuse existing code)
- Use `GammaMarketClient` for selection and `Polymarket` for order ops.
- Reuse helpers from Issues 4–7.

## Scope
- Add `agents/strategies/option_seller.py` implementing grid logic around mid.

## Tasks
- Load config; select 10–20 markets via selection helper.
- Compute mid from orderbook price or outcomePrices.
- Build 3–5 levels per side at 1c spacing; clip sizes from config.
- Inventory-aware widening and flattening on thresholds.
- Refresh quotes on cadence; respect `maker_only`.

## Acceptance Criteria
- Runs in `dry_run` without network order placement; logs intended actions.
- No changes to existing modules.
- Respects per-market EV cap and flatten threshold from config.

## Notes
- Keep logic conservative; no market orders unless flattening (and controlled by config).
