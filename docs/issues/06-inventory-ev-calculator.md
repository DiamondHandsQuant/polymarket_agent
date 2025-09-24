# Issue 6: Inventory/EV calculator and flattening rules

## Background (reuse existing code)
- Persist inventory in `local_state/{bot}/inventory.json` (new), but reuse model concepts from `agents/utils/objects.py`.

## Scope
- Add `agents/strategies/risk_utils.py` to compute EV and actions.

## Tasks
- Implement `compute_market_ev(position_yes, position_no, price_yes)`.
- Implement `decide_action(ev, per_limit, global_ev, global_limit, adverse_move_cents)` → `NONE|WIDEN|PAUSE|FLATTEN`.
- Small helpers for running sums across markets.

## Acceptance Criteria
- Deterministic outputs for given inputs, no network calls.
- Thresholds configurable via caller-provided params.
- Safe defaults if inputs missing.

## Notes
- Keep purely computational; RiskManager wires IO later.
