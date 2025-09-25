from __future__ import annotations

import ast
import json
from typing import Any, Dict, List, Tuple

from agents.strategies.base import BaseBot
from agents.strategies.selection import select_markets_from_cache, compute_mid_price
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


class OptionSellerBot(BaseBot):
    def _tick(self) -> None:
        self._log("option_seller_tick_start")
        try:
            ops: Dict[str, Any] = self.config.get("ops", {})
            quoting_cfg: Dict[str, Any] = self.config.get("quoting", {})
            inventory_cfg: Dict[str, Any] = self.config.get("inventory", {})

            self._log("option_seller_selecting_markets")
            selected = select_markets_from_cache(self.config)
            self._log("option_seller_selected_markets", {"count": len(selected)})
            if not selected:
                self._log("option_seller_no_markets")
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

            clip_usdc_top = float(quoting_cfg.get("clip_usdc_top"))
            clip_usdc_deep = float(quoting_cfg.get("clip_usdc_deep"))

            per_market_ev_cap = float(inventory_cfg.get("per_market_ev_cap"))
            maker_only = bool(inventory_cfg.get("maker_only", True)) or bool(self.config.get("inventory", {}).get("maker_only", True))

            for market in selected:
                self._log(
                    "option_seller_market",
                    {
                        "market_id": market.get("id"),
                        "question": market.get("question"),
                    },
                )
                token_ids = _parse_token_ids(market)
                if not token_ids:
                    self._log("option_seller_no_token_ids", {"market_id": market.get("id")})
                    continue

                token_id = token_ids[0]
                self._log("option_seller_token_ids", {"market_id": market.get("id"), "token_ids": token_ids, "chosen": token_id})

                mid = compute_mid_price(market)
                if mid is None:
                    try:
                        mid = float(self.polymarket.get_orderbook_price(token_id))
                        self._log("option_seller_mid_source", {"market_id": market.get("id"), "source": "orderbook", "mid": mid})
                    except Exception as err:
                        self._log("option_seller_mid_error", {"market_id": market.get("id"), "error": str(err)})
                        continue
                else:
                    self._log("option_seller_mid_source", {"market_id": market.get("id"), "source": "outcomePrices", "mid": mid})

                bids, asks = build_grid(
                    mid=mid,
                    levels_per_side=levels_per_side,
                    level_spacing_cents=level_spacing_cents,
                    base_spread_cents=base_spread_cents,
                    min_spread_cents=min_spread_cents,
                )

                self._log("option_seller_grid_levels", {"market_id": market.get("id"), "bids": bids, "asks": asks})
                if not bids and not asks:
                    self._log("option_seller_empty_grid", {"market_id": market.get("id")})
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
                    self._log("option_seller_ev_cap_trim", {"market_id": market.get("id"), "original_notional": total_notional, "trimmed_notional": running, "per_market_ev_cap": per_market_ev_cap})

                self._log(
                    "option_seller_plan",
                    {
                        "market_id": market.get("id"),
                        "question": market.get("question"),
                        "mid": mid,
                        "token_id": token_id,
                        "levels": [{"side": s, "price": p, "size": sz} for s, p, sz in planned_levels],
                    },
                )

                if maker_only:
                    pass

                for side, price, size in planned_levels:
                    try:
                        self._log("option_seller_place_attempt", {"market_id": market.get("id"), "side": side, "price": price, "size": size, "token_id": token_id})
                        oid = place_limit(price=price, size=size, side=side, token_id=token_id, ctx=ctx)
                        self._log("option_seller_place_result", {"market_id": market.get("id"), "order_id": oid})
                    except Exception as err:
                        self._log("option_seller_place_error", {"market_id": market.get("id"), "error": str(err)})
        except Exception as err:
            self._log("option_seller_tick_error", {"error": str(err)})
        finally:
            self._log("option_seller_tick_complete")


