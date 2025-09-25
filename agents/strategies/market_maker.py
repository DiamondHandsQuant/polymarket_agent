from __future__ import annotations

import ast
import json
from typing import Any, Dict, List, Tuple
import os

from agents.strategies.base import BaseBot
from agents.strategies.selection import select_markets, compute_mid_price
from agents.strategies.quoting import build_grid
from agents.strategies.orders import OrderContext, place_limit


def _parse_token_ids(market: Dict[str, Any]) -> List[str]:
    raw = market.get("clobTokenIds") or market.get("clob_token_ids")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            try:
                return [str(x) for x in json.loads(raw)]
            except json.JSONDecodeError:
                return [str(x) for x in ast.literal_eval(raw)]
        except Exception:
            return []
    return []


class MarketMakerBot(BaseBot):
    def _tick(self) -> None:
        self._log("market_maker_tick_start")
        try:
            ops: Dict[str, Any] = self.config.get("ops", {})
            quoting_cfg: Dict[str, Any] = self.config.get("quoting", {})
            inventory_cfg: Dict[str, Any] = self.config.get("inventory", {})

            self._log("market_maker_selecting_markets")
            # Prefer routed selections if configured
            selected: List[Dict[str, Any]] = []
            routed_path = ops.get("selected_markets_path")
            if routed_path and os.path.exists(routed_path):
                try:
                    with open(routed_path, "r") as f:
                        selected = json.load(f) or []
                    self._log("market_maker_selected_markets_source", {"source": "routed", "path": routed_path})
                except Exception as err:
                    self._log("market_maker_selected_markets_load_error", {"path": routed_path, "error": str(err)})
            if not selected:
                selected = select_markets(self.config)
                self._log("market_maker_selected_markets_source", {"source": "live_selection"})
            self._log("market_maker_selected_markets", {"count": len(selected)})
            if not selected:
                self._log("market_maker_no_markets")
                return

            ctx = OrderContext(
                polymarket=self.polymarket,
                config=self.config,
                state_dir=self._state_dir,
                log_path=self._log_path,
            )

            levels_per_side = int(quoting_cfg.get("levels_per_side"))
            level_spacing_cents = int(quoting_cfg.get("level_spacing_cents"))
            base_spread_cents = int(quoting_cfg.get("base_spread_cents"))
            min_spread_cents = int(quoting_cfg.get("min_spread_cents"))
            skew_k = float(quoting_cfg.get("skew_k", 0.0))

            clip_usdc_top = float(quoting_cfg.get("clip_usdc_top"))
            clip_usdc_deep = float(quoting_cfg.get("clip_usdc_deep"))

            per_market_ev_cap = float(inventory_cfg.get("per_market_ev_cap"))
            maker_only = bool(inventory_cfg.get("maker_only", True)) or bool(self.config.get("inventory", {}).get("maker_only", True))

            for market in selected:
                self._log(
                    "market_maker_market",
                    {
                        "market_id": market.get("id"),
                        "question": market.get("question"),
                    },
                )
                token_ids = _parse_token_ids(market)
                if not token_ids:
                    self._log("market_maker_no_token_ids", {"market_id": market.get("id")})
                    continue

                token_id = token_ids[0]
                self._log("market_maker_token_ids", {"market_id": market.get("id"), "token_ids": token_ids, "chosen": token_id})

                mid = compute_mid_price(market)
                if mid is None:
                    try:
                        mid = float(self.polymarket.get_orderbook_price(token_id))
                        self._log("market_maker_mid_source", {"market_id": market.get("id"), "source": "orderbook", "mid": mid})
                    except Exception as err:
                        self._log("market_maker_mid_error", {"market_id": market.get("id"), "error": str(err)})
                        continue
                else:
                    self._log("market_maker_mid_source", {"market_id": market.get("id"), "source": "outcomePrices", "mid": mid})

                # Inventory skew (if inventory signal exists; else neutral)
                # Placeholder for future position integration
                inventory_ratio = 0.0
                mid_skew = max(0.01, min(0.99, mid + skew_k * inventory_ratio))
                if mid_skew != mid:
                    self._log("market_maker_mid_skew", {"market_id": market.get("id"), "mid": mid, "mid_skew": mid_skew, "skew_k": skew_k})

                bids, asks = build_grid(
                    mid=mid_skew,
                    levels_per_side=levels_per_side,
                    level_spacing_cents=level_spacing_cents,
                    base_spread_cents=base_spread_cents,
                    min_spread_cents=min_spread_cents,
                )

                self._log("market_maker_grid_levels", {"market_id": market.get("id"), "bids": bids, "asks": asks})
                if not bids and not asks:
                    self._log("market_maker_empty_grid", {"market_id": market.get("id")})
                    continue

                planned_levels: List[Tuple[str, float, float]] = []
                for i, p in enumerate(bids):
                    size = clip_usdc_top if i == 0 else clip_usdc_deep
                    planned_levels.append(("BUY", p, size))
                for i, p in enumerate(asks):
                    size = clip_usdc_top if i == 0 else clip_usdc_deep
                    planned_levels.append(("SELL", p, size))

                total_notional = sum(s for _, __, s in planned_levels)
                if per_market_ev_cap and total_notional > per_market_ev_cap:
                    keep: List[Tuple[str, float, float]] = []
                    running = 0.0
                    for entry in planned_levels:
                        if running + entry[2] <= per_market_ev_cap:
                            keep.append(entry)
                            running += entry[2]
                    planned_levels = keep
                    self._log("market_maker_ev_cap_trim", {"market_id": market.get("id"), "original_notional": total_notional, "trimmed_notional": running, "per_market_ev_cap": per_market_ev_cap})

                self._log(
                    "market_maker_plan",
                    {
                        "market_id": market.get("id"),
                        "question": market.get("question"),
                        "mid": mid_skew,
                        "token_id": token_id,
                        "levels": [{"side": s, "price": p, "size": sz} for s, p, sz in planned_levels],
                    },
                )

                if maker_only:
                    pass

                for side, price, size in planned_levels:
                    try:
                        self._log("market_maker_place_attempt", {"market_id": market.get("id"), "side": side, "price": price, "size": size, "token_id": token_id})
                        oid = place_limit(price=price, size=size, side=side, token_id=token_id, ctx=ctx)
                        self._log("market_maker_place_result", {"market_id": market.get("id"), "order_id": oid})
                    except Exception as err:
                        self._log("market_maker_place_error", {"market_id": market.get("id"), "error": str(err)})
        except Exception as err:
            self._log("market_maker_tick_error", {"error": str(err)})
        finally:
            self._log("market_maker_tick_complete")


