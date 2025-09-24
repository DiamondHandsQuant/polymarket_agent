# Issue 7: Order lifecycle (dry-run stubs + Polymarket wiring)

## Background (reuse existing code)
- Use `Polymarket.execute_order` for live posting.
- Use `Polymarket.get_orderbook[_price]` for context when needed.

## Scope
- Add `agents/strategies/orders.py` abstracting place/refresh/cancel with `dry_run` gating.

## Tasks
- Implement `place_limit(price, size, side, token_id, dry_run)` → returns order id or stub.
- Implement `cancel(order_id, dry_run)` and `refresh(open_orders, ttl_s, dry_run)`.
- Add simple rate limit handling (sleep/backoff) using stdlib.

## Acceptance Criteria
- In `dry_run`, only logs; no network calls.
- In live mode, calls Polymarket methods safely and catches exceptions.
- No changes to `Polymarket` itself.

## Notes
- Keep minimal; advanced handling deferred.
