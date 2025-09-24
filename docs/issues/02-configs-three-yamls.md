# Issue 2: Add configs directory with three YAMLs

## Background (reuse existing code)
- Config consumed by new bots only; no changes to existing modules.

## Scope
- Add `configs/option_seller.yaml`, `configs/market_maker.yaml`, `configs/risk.yaml`.
- Each file includes sections: `market_selection`, `quoting` (if applicable), `inventory` (if applicable), `ops`.
- Defaults set to `dry_run: true`.

## Tasks
- Create `configs/` directory.
- Author the three YAMLs with sensible defaults matching the plan.
- Include minimal schema comments in files for readability.

## Acceptance Criteria
- YAML files loadable by `BaseBot` without errors.
- Required keys present: `ops` with `dry_run`, `state_dir`, `log_path` (optional values allowed).
- Values are conservative (no live trading by default).

## Notes
- Do not add a new config loader; reuse `yaml.safe_load` within `BaseBot`.

---
Maintainer comment:
- Created `configs/option_seller.yaml`, `configs/market_maker.yaml`, `configs/risk.yaml` with dry_run defaults.
- Validated by constructing `BaseBot` with each config and running 2–3 seconds; logs and state dirs created.
- Commit: configs added 521bfaa.
