# Code Workflow Diagrams

## Current Workflow (Before Issue 7)

```
┌─────────────────┐
│   CLI Entry     │
│ scripts/cli.py  │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│   Trade.py      │
│ (Demo Runner)   │
└─────────┬───────┘
          │
          v
┌─────────────────┐    ┌─────────────────┐
│   Executor      │◄───┤  GammaClient    │
│ (AI Strategy)   │    │ (Market Data)   │
└─────────┬───────┘    └─────────────────┘
          │
          v
┌─────────────────┐
│   Polymarket    │
│ (Direct API)    │ ──► execute_order() ──► CLOB API
└─────────────────┘
```

## Proposed Workflow (After Issue 7)

```
┌─────────────────┐
│   CLI Entry     │
│ scripts/cli.py  │
└─────────┬───────┘
          │
          v
┌─────────────────┐    ┌─────────────────┐
│   BaseBot       │◄───┤   Config YAML   │
│ (Strategy Bot)  │    │ (dry_run, etc)  │
└─────────┬───────┘    └─────────────────┘
          │
          v
┌─────────────────┐    ┌─────────────────┐
│   Selection/    │◄───┤  GammaClient    │
│   Quoting       │    │ (Market Data)   │
│   Strategies    │    └─────────────────┘
└─────────┬───────┘
          │ (price, size, side, token_id)
          v
┌─────────────────┐
│  orders.py      │ ◄── Config Context
│ (Order Manager) │     (rate limits, retries, etc)
└─────────┬───────┘
          │
          v
    ┌─────────┐
    │dry_run? │
    └────┬────┘
         │
    ┌────v────┐         ┌────────────┐
    │  YES    │         │     NO     │
    │         │         │            │
    │ Log +   │         │ Guards +   │
    │ Stub ID │         │ Polymarket │
    └─────────┘         └─────┬──────┘
                              │
                              v
                    ┌─────────────────┐
                    │   Polymarket    │
                    │ execute_order() │ ──► CLOB API
                    │ cancel_order()  │
                    └─────────────────┘
```

## Detailed Order Flow

```
Strategy Intent
       │
       v
┌─────────────────┐
│  orders.py      │
│ place_limit()   │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│   Dry Run?      │
└─────┬───────────┘
      │
  ┌───v───┐
  │ YES   │
  └───┬───┘
      │
      v
┌─────────────────┐
│ • Log intent    │
│ • Generate stub │
│ • Save to state │
│ • Return stub   │
└─────────────────┘

      │
  ┌───v───┐
  │  NO   │
  └───┬───┘
      │
      v
┌─────────────────┐
│ Rate Limit      │
│ Check & Sleep   │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Price Band      │
│ Validation      │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Idempotency     │
│ (Client Order)  │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Polymarket      │
│ execute_order() │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ Retry Logic     │
│ (if failed)     │
└─────────┬───────┘
          │
          v
┌─────────────────┐
│ • Persist map   │
│ • Return order  │
│ • Log success   │
└─────────────────┘
```

## File Responsibilities

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Layer                            │
├─────────────────────────────────────────────────────────┤
│ scripts/python/cli.py                                   │
│ • Parse commands                                        │
│ • Load config                                           │
│ • Start bots                                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Strategy Layer                         │
├─────────────────────────────────────────────────────────┤
│ agents/strategies/base.py                               │
│ • Config loading                                        │
│ • Logging setup                                         │
│ • Main loop                                             │
│                                                         │
│ agents/strategies/selection.py                          │
│ • Market filtering                                      │
│                                                         │
│ agents/strategies/quoting.py                            │
│ • Price/size calculation                                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   Order Layer                           │
├─────────────────────────────────────────────────────────┤
│ agents/strategies/orders.py                             │
│ • place_limit()                                         │
│ • cancel()                                              │
│ • refresh()                                             │
│ • Dry-run gating                                        │
│ • Rate limiting                                         │
│ • Idempotency                                           │
│ • Retries                                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
├─────────────────────────────────────────────────────────┤
│ agents/polymarket/gamma.py                              │
│ • Market data                                           │
│ • Event data                                            │
│ • Read-only                                             │
│                                                         │
│ agents/polymarket/polymarket.py                         │
│ • execute_order()                                       │
│ • cancel_order() [NEW]                                  │
│ • get_orderbook()                                       │
│ • CLOB client wrapper                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Config Layer                           │
├─────────────────────────────────────────────────────────┤
│ configs/*.yaml                                          │
│ • dry_run: true/false                                   │
│ • Rate limits                                           │
│ • Retry settings                                        │
│ • Price bands                                           │
│ • State directories                                     │
└─────────────────────────────────────────────────────────┘
```

## Key Changes from Issue 7

1. **New `orders.py`**: Central order management with dry-run gating
2. **Config-driven**: All parameters from YAML, no hard-coded values
3. **Separation**: Strategy logic separate from order execution
4. **Safety**: Rate limits, retries, price bands, idempotency
5. **Observability**: Structured logging, state persistence

