# Issue 5: Quoting utilities (ticks, levels, widening)

## Background (reuse existing code)
- Prices are in cents; Polymarket tick is 0.01. No new deps.

## Scope
- Add `agents/strategies/quoting.py` with helpers to:
  - Round to tick
  - Build grid levels given mid, levels per side, spacing (cents), min/base spread
  - Dynamic widening based on inventory skew or volatility flag

## Tasks
- Implement functions: `round_to_tick(x)`, `build_grid(mid, levels, spacing_cents, base_spread_cents, min_spread_cents)`, `apply_widen(levels, addon_cents)`.
- Keep pure functions; no side effects.

## Acceptance Criteria
- Correct rounding to 1c; never propose prices < 0.01 or > 0.99.
- Levels symmetric around mid unless skew applied by caller.
- Unit-light: simple assertions in docstrings or comments.

## Notes
- Inventory skew applied by MarketMaker bot (next issues).

---
Maintainer comment:
- Implemented in `agents/strategies/quoting.py`: `round_to_tick`, `build_grid`, `apply_widen`.
- Smoke test: built grid around mid=0.5 with 3 levels (bids [0.48,0.47,0.46], asks [0.52,0.53,0.54]); widening by 2c produced expected shifts.
- Commit: 273fe14.

---
Closed:
- Date: 2025-09-24
- Commits: 273fe14
