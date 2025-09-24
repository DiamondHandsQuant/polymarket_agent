# Issue 1: Create strategies package and BaseBot scaffold

## Background (reuse existing code)
- Reuse existing clients: `agents/polymarket/polymarket.py` (orders, balances) and `agents/polymarket/gamma.py` (market discovery).
- Reuse models: `agents/utils/objects.py`.
- Reuse CLI pattern from `scripts/python/cli.py` (Typer app).

## Scope
- Add `agents/strategies/` with `base.py` defining `BaseBot` to encapsulate:
  - YAML config loading, minimal schema validation
  - Structured logging and `dry_run` gating
  - Shared clients: `Polymarket`, `GammaMarketClient`
  - Main loop with tick cadence and graceful shutdown
  - State dir bootstrap; no trading logic yet

## Tasks
- Create `agents/strategies/__init__.py` and `agents/strategies/base.py`.
- Implement `BaseBot` methods: `__init__(config_path)`, `start()`, `stop()`, `_tick()` (placeholder), `load_config()`, `setup_logging()`, `setup_state_dir()`.
- Do not change existing modules; only import them.

## Acceptance Criteria
- Importing `BaseBot` has no side effects (no network calls).
- `BaseBot.start()` runs loop, calls `_tick()` per cadence, stops cleanly.
- `dry_run: true` ensures no order placement is attempted.
- Config validation ensures required keys in `ops` exist (allow optional values).

## Notes
- Keep code style consistent with repository; minimal dependencies; no new third-party libs.

---
Maintainer comment:
- Implemented in `agents/strategies/__init__.py` and `agents/strategies/base.py`.
- Dry-run smoke test with `configs/option_seller.yaml`: bot started, ticked, logged, and stopped cleanly.
- Commits: BaseBot scaffold 3b3e47e; verified via CLI in subsequent commits.

---
Closed:
- Date: 2025-09-24
- Commits: 3b3e47e (scaffold), 521bfaa (configs), fa7e675 (CLI), 6ee368e (docs)
