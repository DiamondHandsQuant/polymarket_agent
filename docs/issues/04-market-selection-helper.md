# Issue 4: Market selection helper

## Background (reuse existing code)
- Use `agents/polymarket/gamma.py` (`GammaMarketClient.get_current_markets`, etc.).
- Do not alter existing Gamma client.

## Scope
- Add a helper under `agents/strategies/` (e.g., `selection.py`) to fetch and filter markets:
  - Inputs: min 24h volume, max spread (cents), mid band [low, high], exclude tags, limit N
  - Output: list of market dicts/objects ready for quoting

## Tasks
- Implement functions to:
  - Fetch recent active markets via `GammaMarketClient`
  - Compute mid from `outcomePrices` when present
  - Filter by spread and mid band, handle missing data safely
  - Sort by volume (fallback to volumeClob/volume24hr if present)

## Acceptance Criteria
- Returns at most N markets meeting filters; never throws on missing fields.
- Pure helper; no network logic beyond Gamma client calls.
- Unit-light: simple self-check/logs for missing fields.

## Notes
- Keep as simple functions; avoid adding new classes.
