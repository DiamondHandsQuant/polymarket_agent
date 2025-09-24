from __future__ import annotations

from typing import Dict, List, Tuple


def compute_market_ev(position_yes: float, position_no: float, price_yes: float) -> float:
    """
    Expected value exposure in USD terms for a binary market given current price of YES.
    - position_yes: net YES shares (positive long, negative short)
    - position_no: net NO shares (positive long, negative short)
    - price_yes: current probability for YES in 0..1

    Returns EV = position_yes * price_yes + position_no * (1 - price_yes)
    """
    if price_yes is None or not (0.0 <= price_yes <= 1.0):
        raise ValueError("price_yes must be within [0,1]")
    if position_yes is None or position_no is None:
        raise ValueError("positions must be provided")
    return float(position_yes) * float(price_yes) + float(position_no) * float(1.0 - price_yes)


def sum_global_ev(market_evs: List[float]) -> float:
    if market_evs is None:
        raise ValueError("market_evs must be provided")
    return float(sum(market_evs))


ACTION_NONE = "NONE"
ACTION_WIDEN = "WIDEN"
ACTION_PAUSE = "PAUSE"
ACTION_FLATTEN = "FLATTEN"


def decide_action(
    ev_abs: float,
    per_limit: float,
    global_ev_abs: float,
    global_limit: float,
    adverse_move_cents: float,
    adverse_threshold_cents: float,
) -> str:
    """
    Decide action based on per-market and global EV limits and recent adverse move.
    - ev_abs: absolute per-market EV exposure
    - per_limit: per-market EV cap
    - global_ev_abs: absolute global EV exposure across markets
    - global_limit: global EV cap
    - adverse_move_cents: recent adverse price move in cents
    - adverse_threshold_cents: threshold in cents to trigger widen/pause

    Priority: FLATTEN if per or global limit breached; else PAUSE/WIDEN on adverse move; else NONE.
    """
    # Validate inputs explicitly
    for name, v in (
        ("per_limit", per_limit),
        ("global_limit", global_limit),
        ("ev_abs", ev_abs),
        ("global_ev_abs", global_ev_abs),
        ("adverse_move_cents", adverse_move_cents),
        ("adverse_threshold_cents", adverse_threshold_cents),
    ):
        if v is None:
            raise ValueError(f"{name} must be provided")
    if per_limit <= 0 or global_limit <= 0:
        raise ValueError("limits must be positive")

    if ev_abs >= per_limit or global_ev_abs >= global_limit:
        return ACTION_FLATTEN

    if adverse_move_cents >= adverse_threshold_cents:
        # Caller can map WIDEN/PAUSE to concrete spread changes; we return WIDEN by default
        return ACTION_WIDEN

    return ACTION_NONE
