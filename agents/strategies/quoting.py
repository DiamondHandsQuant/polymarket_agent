from __future__ import annotations

from typing import List, Tuple

TICK = 0.01
MIN_PRICE = 0.01
MAX_PRICE = 0.99


def round_to_tick(x: float, tick: float = TICK) -> float:
    v = max(MIN_PRICE, min(MAX_PRICE, x))
    # Avoid floating drift by using integer math
    n = int(round(v / tick))
    return max(MIN_PRICE, min(MAX_PRICE, n * tick))


def build_grid(
    mid: float,
    levels_per_side: int,
    level_spacing_cents: int,
    base_spread_cents: int,
    min_spread_cents: int,
) -> Tuple[List[float], List[float]]:
    """
    Returns (bids, asks) price levels around mid.
    - mid: 0..1 probability.
    - levels_per_side: number of price levels on each side.
    - level_spacing_cents: spacing between levels in cents.
    - base_spread_cents: target half-spread in cents from mid for top level.
    - min_spread_cents: minimal half-spread from mid for top level.
    """
    if levels_per_side <= 0:
        return [], []

    spacing = level_spacing_cents / 100.0
    half = max(min_spread_cents, base_spread_cents) / 100.0

    bids: List[float] = []
    asks: List[float] = []

    for i in range(levels_per_side):
        offset = half + i * spacing
        bids.append(round_to_tick(mid - offset))
        asks.append(round_to_tick(mid + offset))

    # Deduplicate and keep sorted best to worst
    bids = sorted(list(dict.fromkeys([p for p in bids if p >= MIN_PRICE])), reverse=True)
    asks = sorted(list(dict.fromkeys([p for p in asks if p <= MAX_PRICE])))
    return bids, asks


def apply_widen(levels: List[float], addon_cents: int, side: str) -> List[float]:
    """
    Widen existing levels by addon_cents away from mid depending on side.
    - side: 'bid' or 'ask'
    """
    addon = addon_cents / 100.0
    if side == 'bid':
        return [round_to_tick(p - addon) for p in levels if p - addon >= MIN_PRICE]
    else:
        return [round_to_tick(p + addon) for p in levels if p + addon <= MAX_PRICE]
