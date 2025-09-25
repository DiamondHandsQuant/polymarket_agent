# Issue 7: Order lifecycle (dry-run stubs + Polymarket wiring)

## Background (reuse existing code)
- Use `Polymarket.execute_order` for live posting.
- Use `Polymarket.get_orderbook[_price]` for price context/guards.

## Scope
- Add `agents/strategies/orders.py` as the central order entrypoint, abstracting `place_limit`, `cancel`, and `refresh` with `dry_run` gating and config-driven safety.
- Orders layer enforces: pacing/rate-limit, bounded retries with backoff+jitter, idempotency (client order IDs), basic price-band guard, minimal persistence, startup reconciliation, and structured logging.
- Allow a minimal `Polymarket.cancel_order(order_id)` thin wrapper (delegation only) if required; no other changes to `Polymarket`.

## Tasks
1) Create `agents/strategies/orders.py` with the following functions (no hard-coded values; read from provided context/config):
   - `place_limit(price, size, side, token_id, ctx)` → returns exchange order id (live) or stub id (dry-run).
     - Dry-run path: structured log; generate deterministic stub id; persist intent to `ops.state_dir`; return stub id.
     - Live path: enforce pacing, price-band validation vs `Polymarket.get_orderbook_price(token_id)`, idempotency (client order id), then call `Polymarket.execute_order(...)`. On failure, apply bounded backoff/retry governed by config. Persist client→exchange id map and timestamps; return exchange order id.
   - `cancel(order_id, ctx)` → dry-run logs only; live delegates to `Polymarket.cancel_order(order_id)` (or directly to CLOB cancel if available through the wrapped client), with retries/backoff from config.
   - `refresh(open_orders, ttl_s, ctx)` → for each order exceeding `ttl_s`, perform cancel/replace flow per strategy signal. Dry-run logs only; live performs actions guarded by pacing/idempotency.

2) Persistence and observability
   - Persist minimal state under `ops.state_dir`: client order id, exchange order id, created_at, attempts, last_error, cancel_requested flags.
   - Structured logs to `ops.log_path` with fields: `token_id`, `side`, `price`, `size`, `client_order_id`, `exchange_order_id`, `attempt`, `reason`, `latency_ms`.

3) Rate limiting and retries (stdlib only)
   - Pacing: sleep to satisfy a configured minimum inter-order interval; include random jitter from config.
   - Retries: exponential or multiplicative backoff with jitter; cap attempts and total time strictly per config. Classify simple transient errors (HTTP timeouts/5xx) as retryable.

4) Idempotency and concurrency
   - Generate client order IDs deterministically (e.g., hash of tuple `(token_id, side, price, size, logical_intent_id, timestamp_bucket)`), per config rules. Deduplicate local submits on retry.
   - Optional per-market lock to prevent duplicate simultaneous submits; scope and behavior driven by config.

5) Optional thin wrapper in `agents/polymarket/polymarket.py`
   - Add `cancel_order(order_id: str) -> str | dict` delegating directly to the underlying CLOB client/HTTP API with no business logic. Keep `execute_order` unchanged.

6) Wiring
   - Ensure strategy modules (selection/quoting) call `orders.place_limit(...)` and never call `Polymarket.execute_order(...)` directly.
   - Keep `GammaMarketClient` read-only (markets/events).

## Config (no defaults in code)
- All behavior must be driven by YAML under `ops` (names are illustrative; actual values provided by user config):
  - `ops.dry_run`
  - `ops.state_dir`, `ops.log_path`
  - `ops.rate_limit.min_interval_seconds`, `ops.rate_limit.jitter_ms`
  - `ops.retry.max_attempts`, `ops.retry.base_sleep_seconds`, `ops.retry.jitter_ms`, `ops.retry.max_total_seconds`
  - `ops.price_band.max_bps_from_mid` (validate limit price within band of mid/last)
  - `ops.spend_caps.max_orders_per_interval`, `ops.spend_caps.interval_seconds` (optional, if used)
  - `ops.concurrency.enable_per_market_lock` (optional)
  - `ops.refresh.ttl_seconds` (used by `refresh`)

## Acceptance Criteria
- Dry-run: only structured logs and local state writes; zero network calls to order endpoints.
- Live: delegates to `Polymarket` for execution; cancellation is permitted via a thin `cancel_order` wrapper if needed. All failures are caught and handled with bounded, config-driven retries/backoff.
- No hard-coded thresholds; all timings, limits, bands, and toggles sourced from config.
- Idempotency: duplicate post attempts for the same client order are prevented locally.
- Pacing: inter-order spacing honored according to config; jitter applied.
- Persistence: client↔exchange id mapping and attempt metadata written under `ops.state_dir`.
- Logging: per-order structured logs written to `ops.log_path`.
- No strategy or Polymarket business logic leaks into `orders.py` beyond delegation and guardrails.

## Notes
- Keep minimal; advanced handling (full state machine, event-driven updates, deep simulation) remains out of scope.
