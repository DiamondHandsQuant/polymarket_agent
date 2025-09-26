# Issue 10: Implement RiskManager (global controller) - ✅ COMPLETED

## Background (reuse existing code)
- Reuse EV helpers (Issue 6). Avoid modifying order modules.

## Scope
- Add `agents/strategies/risk.py` to monitor states and issue actions.

### Integration with selection/refresh/routing
- Consume routed markets via `ops.selected_markets_path` when present (no network calls).
- Use centralized cache from Issue 13 if needed for EV context, but prefer routed inputs.
- Align with orchestrator flow in Issue 14: selection -> cache/Chroma -> routing -> risk actions.

## Tasks
- ✅ Poll `local_state/{bot}/` inventories and PnL snapshots.
- ✅ Compute per-market and global EV; apply daily PnL kill.
- ✅ Write `actions/{bot}.json` with `NONE|WIDEN|PAUSE|FLATTEN` signals.
- ✅ Read routed selections for Risk Manager from `ops.selected_markets_path` if configured.
- ✅ Add configurable paths under `ops`: `state_dir`, `actions_dir`, `selected_markets_path`.

## Acceptance Criteria
- ✅ No network calls; file-based communication only.
- ✅ Conservative defaults; never triggers live orders directly.
- ✅ Clean logs of breaches and actions.
- ✅ Consumes routed selections when available; otherwise operates on current on-disk bot states.

## Status
- ✅ Scaffold implemented: `agents/strategies/risk.py`
- ✅ CLI wired: `run-risk-manager` command
- ✅ Actions emitted to `local_state/risk_manager/actions/risk_actions.json`
- ✅ Config updated: `configs/risk.yaml` with `actions_dir`, `monitor_bots`

## Notes
- Bots poll actions and react; RiskManager does not edit bot configs.
- See Issues 13 and 14 for the selection/refresh/routing workflow.

## Runbook (file-driven workflow)
```bash
# 1) Refresh markets and route (prior step managed by orchestrator/CLI)
PYTHONPATH=. python3 scripts/python/cli.py refresh-markets --config configs/risk.yaml --limit 20 --fetch-limit 50 --skip-classify
PYTHONPATH=. python3 scripts/python/cli.py route-markets \
  --source-config configs/risk.yaml \
  --risk-manager-config configs/risk.yaml --risk-manager-limit 50 --risk-manager-output local_state/risk_manager/selected_markets.json \
  --market-maker-config configs/market_maker.yaml --market-maker-output local_state/market_maker/selected_markets.json \
  --option-seller-config configs/option_seller.yaml --option-seller-output local_state/option_seller/selected_markets.json

# 2) Run Risk Manager (reads from selected_markets_path/state_dir and writes actions_dir)
PYTHONPATH=. python3 scripts/python/cli.py run-risk-manager --config configs/risk.yaml --duration 60
```
