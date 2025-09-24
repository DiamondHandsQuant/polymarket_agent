# Issue 3: Wire CLI commands for three bots

## Background (reuse existing code)
- Extend `scripts/python/cli.py` (Typer) with new commands; keep existing commands intact.

## Scope
- Add commands: `run_option_seller`, `run_market_maker`, `run_risk_manager`.
- Each accepts `--config` path; instantiates respective bot and calls `start()`.
- Ensure clean shutdown via KeyboardInterrupt handling.

## Tasks
- Import new classes from `agents/strategies`.
- Implement the three Typer commands with docstrings and help.
- Log startup config path and `dry_run` status.

## Acceptance Criteria
- `python scripts/python/cli.py run_option_seller --config configs/option_seller.yaml` starts without errors (dry-run).
- Commands do not post orders in `dry_run`.
- No changes to existing commands' behavior.

## Notes
- Avoid global side effects on import; construct bots inside commands.
