from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agents.polymarket.polymarket import Polymarket


@dataclass
class OrderContext:
    polymarket: Polymarket
    config: Dict[str, Any]
    state_dir: str
    log_path: Optional[str]

    @property
    def dry_run(self) -> bool:
        return bool(self.config.get("ops", {}).get("dry_run"))


def _log(ctx: OrderContext, message: str, payload: Dict[str, Any] | None = None) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line: Dict[str, Any] = {"ts": ts, "msg": message}
    if payload:
        line.update(payload)
    print(json.dumps(line))
    try:
        if ctx.log_path:
            os.makedirs(os.path.dirname(ctx.log_path), exist_ok=True)
            with open(ctx.log_path, "a") as f:
                f.write(json.dumps(line) + "\n")
    except Exception:
        pass


def _ensure_orders_state_dir(ctx: OrderContext) -> str:
    path = os.path.join(ctx.state_dir, "orders")
    os.makedirs(path, exist_ok=True)
    return path


def _persist_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _append_open_orders(ctx: OrderContext, record: Dict[str, Any]) -> None:
    try:
        oo_path = os.path.join(ctx.state_dir, "open_orders.json")
        current: Dict[str, Any] = {"orders": []}
        if os.path.exists(oo_path):
            with open(oo_path, "r") as f:
                try:
                    current = json.load(f) or {"orders": []}
                except Exception:
                    current = {"orders": []}
        orders_list = current.get("orders", [])
        orders_list.append(record)
        current["orders"] = orders_list
        _persist_json(oo_path, current)
    except Exception:
        pass


def _deterministic_client_order_id(token_id: str, side: str, price: float, size: float, extra: str) -> str:
    payload = f"{token_id}|{side}|{price}|{size}|{extra}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _pacing_sleep(ctx: OrderContext) -> None:
    ops = ctx.config.get("ops", {})
    rate_limit = ops.get("rate_limit", {})
    min_interval = float(rate_limit.get("min_interval_seconds", 0))
    jitter_ms = int(rate_limit.get("jitter_ms", 0))
    if min_interval > 0:
        time.sleep(min_interval)
    if jitter_ms > 0:
        time.sleep(random.uniform(0, jitter_ms / 1000.0))


def _within_price_band(ctx: OrderContext, token_id: str, price: float) -> bool:
    ops = ctx.config.get("ops", {})
    band = ops.get("price_band", {})
    max_bps = band.get("max_bps_from_mid")
    if max_bps is None:
        return True
    try:
        # Use BUY side to get current price; could also average both sides
        mid = float(ctx.polymarket.get_orderbook_price(token_id))
    except Exception as err:
        _log(ctx, "order_price_band_mid_error", {"error": str(err)})
        return False
    diff_bps = abs(price - mid) / max(mid, 1e-9) * 10000.0
    return diff_bps <= float(max_bps)


def place_limit(price: float, size: float, side: str, token_id: str, ctx: OrderContext) -> str:
    state_dir = _ensure_orders_state_dir(ctx)
    extra = time.strftime("%Y%m%d%H%M")  # caller can supply a better bucket if desired
    client_order_id = _deterministic_client_order_id(token_id, side, price, size, extra)

    payload = {
        "token_id": token_id,
        "side": side,
        "price": price,
        "size": size,
        "client_order_id": client_order_id,
    }

    if ctx.dry_run:
        _log(ctx, "order_place_dry_run", payload)
        stub = {"id": f"stub_{client_order_id}", "status": "DRY_RUN"}
        record = {**payload, **stub, "created_at_ts": time.time()}
        _persist_json(os.path.join(state_dir, f"{client_order_id}.json"), record)
        _append_open_orders(ctx, record)
        return stub["id"]

    # Live path
    if not _within_price_band(ctx, token_id, price):
        _log(ctx, "order_rejected_price_band", {**payload, "reason": "price_band"})
        raise ValueError("price outside allowed band")

    _pacing_sleep(ctx)

    # Idempotency: if mapping already exists, return it instead of re-posting
    mapping_path = os.path.join(state_dir, f"{client_order_id}.json")
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, "r") as f:
                saved = json.load(f)
                exchange_id = saved.get("exchange_order_id")
                if exchange_id:
                    _log(ctx, "order_place_idempotent_hit", {**payload, "exchange_order_id": exchange_id})
                    return exchange_id
        except Exception:
            pass

    ops = ctx.config.get("ops", {})
    retry = ops.get("retry", {})
    max_attempts = int(retry.get("max_attempts", 1))
    base_sleep = float(retry.get("base_sleep_seconds", 0))
    jitter_ms = int(retry.get("jitter_ms", 0))

    attempt = 0
    last_err: Optional[str] = None

    while attempt < max_attempts:
        attempt += 1
        t0 = time.time()
        try:
            exchange_order_id = ctx.polymarket.execute_order(price, size, side, token_id)
            latency_ms = int((time.time() - t0) * 1000)
            record = {
                **payload,
                "exchange_order_id": exchange_order_id,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "created_at_ts": time.time(),
                "attempt": attempt,
                "latency_ms": latency_ms,
            }
            _persist_json(mapping_path, record)
            _append_open_orders(ctx, record)
            _log(ctx, "order_place_success", record)
            return exchange_order_id
        except Exception as err:
            last_err = str(err)
            _log(ctx, "order_place_error", {**payload, "attempt": attempt, "error": last_err})
            if attempt >= max_attempts:
                break
            sleep_for = base_sleep * (2 ** (attempt - 1))
            if jitter_ms > 0:
                sleep_for += random.uniform(0, jitter_ms / 1000.0)
            time.sleep(max(sleep_for, 0.0))

    raise RuntimeError(f"order placement failed after {max_attempts} attempts: {last_err}")


def cancel(order_id: str, ctx: OrderContext) -> None:
    state_dir = _ensure_orders_state_dir(ctx)
    if ctx.dry_run:
        _log(ctx, "order_cancel_dry_run", {"order_id": order_id})
        return

    ops = ctx.config.get("ops", {})
    retry = ops.get("retry", {})
    max_attempts = int(retry.get("max_attempts", 1))
    base_sleep = float(retry.get("base_sleep_seconds", 0))
    jitter_ms = int(retry.get("jitter_ms", 0))

    attempt = 0
    last_err: Optional[str] = None
    while attempt < max_attempts:
        attempt += 1
        try:
            # Thin delegate; requires Polymarket.cancel_order to exist
            if not hasattr(ctx.polymarket, "cancel_order"):
                raise NotImplementedError("cancel_order not available on Polymarket client")
            ctx.polymarket.cancel_order(order_id)
            _log(ctx, "order_cancel_success", {"order_id": order_id, "attempt": attempt})
            return
        except Exception as err:
            last_err = str(err)
            _log(ctx, "order_cancel_error", {"order_id": order_id, "attempt": attempt, "error": last_err})
            if attempt >= max_attempts:
                break
            sleep_for = base_sleep * (2 ** (attempt - 1))
            if jitter_ms > 0:
                sleep_for += random.uniform(0, jitter_ms / 1000.0)
            time.sleep(max(sleep_for, 0.0))

    raise RuntimeError(f"order cancel failed after {max_attempts} attempts: {last_err}")


def refresh(open_orders: list[Dict[str, Any]], ttl_s: int, ctx: OrderContext) -> None:
    now = time.time()
    for od in open_orders:
        try:
            created_at = od.get("created_at_ts")
            order_id = od.get("exchange_order_id")
            token_id = od.get("token_id")
            side = od.get("side")
            price = float(od.get("price"))
            size = float(od.get("size"))
            if not created_at or not order_id:
                continue
            if now - float(created_at) < float(ttl_s):
                continue

            if ctx.dry_run:
                _log(ctx, "order_refresh_dry_run", {"order_id": order_id})
                continue

            # Replace flow: cancel and resubmit can be strategy-driven; here we do basic TTL replace
            cancel(order_id, ctx)
            place_limit(price, size, side, token_id, ctx)
        except Exception as err:
            _log(ctx, "order_refresh_error", {"order": od, "error": str(err)})


