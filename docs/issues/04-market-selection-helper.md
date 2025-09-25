# Issue 4: Market selection helper

## Background (reuse existing code)
- Use `agents/polymarket/gamma.py` (`GammaMarketClient.get_current_markets`, etc.) for market discovery and numeric filters (volume/spread/mid).
- Prefer LLM-based classification for categories (uses existing `Executor`/OpenAI plumbing and new prompts in `agents/application/prompts.py`).
- Subgraph enrichment optional later; not required for initial delivery.

## Scope
- Add `agents/strategies/selection.py` to fetch, classify, and filter markets:
  - Inputs: min 24h volume, max spread (cents), mid band [low, high], limit N
  - Classification: primary = LLM (categories: politics, crypto, sports, finance, tech, science, entertainment, other)
  - Output: list of market dicts with `category` and computed `mid`, sorted and limited
  - Implement caching to avoid repeated LLM calls

## Tasks
- Implement functions:
  - `compute_mid_price(mkt) -> float|None`, `get_volume(mkt) -> float`, `get_spread_cents(mkt) -> float|None`
  - `classify_market_llm(mkt) -> category` using prompts: `classify_market_category` (single) or `classify_markets_batch` (batch)
  - `market_passes_filters(mkt, cfg) -> bool`
  - `select_markets(cfg) -> list[mkt_with_category]` (fetch via Gamma + classify + filter + sort + limit)
- Add on-disk cache: `local_state/category_cache.json` with TTL; never call LLM if cache hit and fresh
- Sort by `volume` then fallbacks (volume24hr/volumeClob) as available

## Config keys (under each bot's market_selection)
- `source: llm` (options: `llm`, `gamma_only`, `subgraph_only` in future)
- `min_volume_24h: int`
- `max_spread_cents: int`
- `mid_price_band: [float, float]`
- `limit: int`
- `cache_path: local_state/category_cache.json`
- `cache_ttl_hours: 24`
- `llm_model: gpt-4o-mini` (or use default in `Executor`)
- (Optional later) `subgraph_url` if we enable enrichment

## Acceptance Criteria
- Returns at most N markets; never throws on missing fields.
- Each returned market includes `category` (LLM-derived) and computed `mid` (float).
- Respects numeric filters; avoids LLM calls when cache is valid.
- Batch classification path works and falls back to single-item classification on errors; invalid JSON yields `other`.

## Notes
- Stateless apart from cache; all tunables are config-driven.
- We will log category assignments and cache hits for observability.

---
Maintainer comment:
- Implemented `agents/strategies/selection.py` with LLM-only classification (cached) and Gamma metrics (volume/spread/mid). Prompts added in `agents/application/prompts.py`.
- Dry-run verified categories populate (e.g., crypto) and cache persists to `local_state/category_cache.json`.
- Subgraph path removed as requested; no optional imports remain.
- Commits: selection helper a10d8f2, LLM integration 8e8aefe, optionality removal f1c17fd → final LLM-only ad05afb; issue update 1216dda.

---
Closed:
- Date: 2025-09-24
- Commits: a10d8f2, 8e8aefe, f1c17fd, ad05afb, 1216dda

### See also
- `docs/issues/13-market-selection-refresh-and-cache.md`
