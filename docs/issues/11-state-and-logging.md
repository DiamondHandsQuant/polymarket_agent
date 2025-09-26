# Issue 11: Persistent state and logging - ✅ COMPLETED

## Background (reuse existing code)
- Follow pattern of local db dirs already present; do not change them.

## Scope
- Introduce `local_state/{bot}/` for positions/inventory/open orders and `logs/{bot}.log`.

## Tasks
- ✅ Ensure `BaseBot` creates state dir and logger per config.
- ✅ Define filenames: `positions.json`, `inventory.json`, `open_orders.json`.

### Follow-ups
- Add `.gitignore` entries for `local_state/` and `logs/` if desired.

## Acceptance Criteria
- State directory created and log file appended in `dry_run` on first run. ✅
- Example state artifacts exist (per-order JSONs under `orders/`, aggregate `open_orders.json`). ✅

## Notes
- Keep JSON format stable and minimal; bots and RiskManager rely on it.

## Status
- ✅ Completed. `BaseBot` initializes state files; bots write per-order JSONs and maintain `open_orders.json`.
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
