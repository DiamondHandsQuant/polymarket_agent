# Issue 10: Implement RiskManager (global controller)

## Background (reuse existing code)
- Reuse EV helpers (Issue 6). Avoid modifying order modules.

## Scope
- Add `agents/strategies/risk.py` to monitor states and issue actions.

## Tasks
- Poll `local_state/{bot}/` inventories and PnL snapshots.
- Compute per-market and global EV; apply daily PnL kill.
- Write `actions/{bot}.json` with `NONE|WIDEN|PAUSE|FLATTEN` signals.

## Acceptance Criteria
- No network calls; file-based communication only.
- Conservative defaults; never triggers live orders directly.
- Clean logs of breaches and actions.

## Notes
- Bots poll actions and react; RiskManager does not edit bot configs.
