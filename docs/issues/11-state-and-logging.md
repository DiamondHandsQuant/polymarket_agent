# Issue 11: Persistent state and logging

## Background (reuse existing code)
- Follow pattern of local db dirs already present; do not change them.

## Scope
- Introduce `local_state/{bot}/` for positions/inventory/open orders and `logs/{bot}.log`.

## Tasks
- Ensure `BaseBot` creates state dir and logger per config.
- Define filenames: `positions.json`, `inventory.json`, `open_orders.json`.
- Update `.gitignore` if needed to exclude `local_state/` and `logs/`.

## Acceptance Criteria
- State files created in `dry_run` with example content on first run.
- Log rotation configured or file grows safely (time/size configurable later).

## Notes
- Keep JSON format stable and minimal; bots and RiskManager rely on it.
