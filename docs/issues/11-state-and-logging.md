# Issue 11: Persistent state and logging

## Background (reuse existing code)
- Follow pattern of local db dirs already present; do not change them.

## Scope
- Introduce `local_state/{bot}/` for positions/inventory/open orders and `logs/{bot}.log`.

## Tasks
- ✅ Ensure `BaseBot` creates state dir and logger per config.
- ⏳ Define filenames: `positions.json`, `inventory.json`, `open_orders.json`.
- ⏳ Update `.gitignore` if needed to exclude `local_state/` and `logs/`.

## Acceptance Criteria
- State directory created and log file appended in `dry_run` on first run. ✅
- Example state artifacts exist (currently per-order JSONs under `orders/`). ✅
- Log rotation configured or file grows safely (time/size configurable later). ⏳

## Notes
- Keep JSON format stable and minimal; bots and RiskManager rely on it.

## Status
- Base scaffolding complete: `BaseBot` creates `ops.state_dir` and appends to `ops.log_path`.
- Bots emit per-order JSONs in `local_state/{bot}/orders/` when `dry_run` places orders.
- Risk Manager reads `orders/` and `selected_markets.json` to compute actions.

## Runbook
```bash
# Run a bot briefly to create state dir and logs (dry run)
PYTHONPATH=. python3 scripts/python/cli.py run-option-seller --config configs/option_seller.yaml --duration 10

# Check that directories/files exist
ls -la local_state/option_seller
ls -la logs/ | grep option_seller

# (Optional) Risk Manager writes actions snapshot
PYTHONPATH=. python3 scripts/python/cli.py run-risk-manager --config configs/risk.yaml --duration 10
cat local_state/risk_manager/actions/risk_actions.json
```
