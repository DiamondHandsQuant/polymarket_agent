from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from agents.strategies.base import BaseBot
from agents.strategies.risk_utils import (
    ACTION_FLATTEN,
    ACTION_NONE,
    ACTION_PAUSE,
    ACTION_WIDEN,
    compute_market_ev,
    decide_action,
    sum_global_ev,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


class RiskManagerBot(BaseBot):
    """
    File-driven Risk Manager:
    - Reads inventories and routed selections from disk
    - Computes per-market EV and global EV exposure
    - Emits actions per bot to actions_dir
    """

    def __init__(self, config_path: str) -> None:
        super().__init__(config_path)
        ops = self.config.get("ops", {})
        self.actions_dir = ops.get("actions_dir", os.path.join(self.state_dir, "actions"))
        os.makedirs(self.actions_dir, exist_ok=True)

    def _load_bot_state(self, bot_name: str, bot_dir: str) -> Dict[str, Any]:
        state: Dict[str, Any] = {"orders": [], "positions": {}, "selected": []}

        # Load routed selections if present
        sel_path = os.path.join(bot_dir, "selected_markets.json")
        try:
            if os.path.exists(sel_path):
                with open(sel_path, "r") as f:
                    state["selected"] = json.load(f)
        except Exception:
            state["selected"] = []

        # Load orders directory as current exposure proxy
        orders_dir = os.path.join(bot_dir, "orders")
        orders: List[Dict[str, Any]] = []
        if os.path.isdir(orders_dir):
            for fn in os.listdir(orders_dir):
                if not fn.endswith(".json"):
                    continue
                fp = os.path.join(orders_dir, fn)
                try:
                    with open(fp, "r") as f:
                        od = json.load(f)
                        orders.append(od)
                except Exception:
                    continue
        state["orders"] = orders

        return state

    def _tick(self) -> None:
        ops = self.config.get("ops", {})
        risk_cfg = self.config.get("risk", {})

        per_cap = _safe_float(risk_cfg.get("per_market_ev_cap", 1000.0))
        global_cap = _safe_float(risk_cfg.get("global_ev_cap", 5000.0))
        adverse_thresh_cents = _safe_float(risk_cfg.get("fast_move_cents", 10.0))

        monitor = ops.get("monitor_bots", ["market_maker", "option_seller"])  # directories under local_state/
        local_state_root = ops.get("local_state_root", "local_state")

        per_market_actions: Dict[str, str] = {}
        market_evs: List[float] = []

        for bot in monitor:
            bot_dir = os.path.join(local_state_root, bot)
            state = self._load_bot_state(bot, bot_dir)

            # Aggregate exposure per token_id from orders as a proxy
            positions: Dict[str, Dict[str, float]] = {}
            for od in state.get("orders", []):
                token_id = str(od.get("token_id"))
                side = (od.get("side") or "").upper()
                size = _safe_float(od.get("size"), 0.0)
                if token_id not in positions:
                    positions[token_id] = {"YES": 0.0, "NO": 0.0}
                positions[token_id][side] = positions[token_id].get(side, 0.0) + size

            # Compute EV per selected market (use mid if available)
            for m in state.get("selected", []):
                token_ids = m.get("clobTokenIds") or m.get("clob_token_ids") or []
                yes_token = str(token_ids[0]) if isinstance(token_ids, list) and token_ids else None
                mid = _safe_float(m.get("mid"), None)
                if yes_token is None or mid is None:
                    continue
                pos = positions.get(yes_token, {"YES": 0.0, "NO": 0.0})
                ev = compute_market_ev(pos.get("YES", 0.0), pos.get("NO", 0.0), mid)
                ev_abs = abs(ev)
                market_evs.append(ev)

                # Placeholder adverse move: use 0 in file-driven mode
                adverse_move_cents = 0.0
                action = decide_action(
                    ev_abs=ev_abs,
                    per_limit=per_cap,
                    global_ev_abs=0.0,  # temp, will fill after global calc
                    global_limit=global_cap,
                    adverse_move_cents=adverse_move_cents,
                    adverse_threshold_cents=adverse_thresh_cents,
                )
                market_id = str(m.get("id"))
                per_market_actions[market_id] = action

        # Compute global EV after per-market loop
        global_ev = sum_global_ev([abs(x) for x in market_evs]) if market_evs else 0.0
        # If global exceeds, upgrade severe action for all
        if global_ev >= global_cap:
            for k in list(per_market_actions.keys()):
                per_market_actions[k] = ACTION_FLATTEN

        # Persist actions atomically
        actions_path = os.path.join(self.actions_dir, "risk_actions.json")
        tmp = actions_path + ".tmp"
        payload = {
            "global_ev_abs": abs(global_ev),
            "global_cap": global_cap,
            "per_market": per_market_actions,
        }
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, actions_path)
        self._log("risk_tick", {"global_ev_abs": abs(global_ev), "num_markets": len(per_market_actions)})


