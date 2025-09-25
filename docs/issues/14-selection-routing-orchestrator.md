## Issue 14: Centralized selection → Chroma → routing to bots

### Summary
Introduce a single orchestration flow that selects markets once, persists to cache/Chroma, then routes markets to the three bots based on config-driven policies.

### Motivation
- Eliminate duplicated selection logic across bots.
- Ensure all bots act on the same fresh snapshot.
- Keep selection thresholds/config in one place, with per-bot routing policies layered on top.

### Proposed Flow
1) Selection
   - `selection.select_markets(cfg)` (or `refresh-markets` CLI) fetches/filters (optionally classifies) and persists to
     - `local_db_markets/markets.json`
     - `local_db_markets/chroma`
   - See Issue 13 for details.

2) Routing
   - New module: `agents/application/router.py`
   - Inputs: cached markets JSON and/or Chroma queries.
   - Policies (from YAML): per-bot constraints (volume, spread, mid band, categories/tags), overlap resolution, max per-bot.
   - Outputs: per-bot selection files
     - `local_state/option_seller/selected_markets.json`
     - `local_state/market_maker/selected_markets.json`
     - `local_state/risk_manager/selected_markets.json`

3) Execution
   - Bots load their `selected_markets.json` first; optional fallback to live `select_markets(cfg)`.

### CLI
- New: `route-markets` (reads cache, writes per-bot selections)
  - Flags: `--config`, `--option-seller-limit`, `--market-maker-limit`, `--risk-limit`, plus tag/category filters.
  - Deterministic assignment with priority rules to avoid double-allocation unless allowed.

### Acceptance Criteria
- Single refresh followed by routing deterministically produces three per-bot selection files.
- Bots consume those files without code changes (or minimal opt-in change).
- Fully config-driven; no hardcoded thresholds.

### Follow-ups
- Scheduler to run: refresh-markets → route-markets at TTL.
- Metrics/health logging: selected counts per bot and rejection reasons.

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`
- `docs/issues/08-option-seller-bot.md`
- `docs/issues/09-market-maker-bot.md`

