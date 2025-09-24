from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Tuple

from agents.polymarket.gamma import GammaMarketClient


def _safe_get_prices(market: Dict[str, Any]) -> List[float]:
    raw = market.get("outcomePrices")
    prices: List[float] = []
    if raw is None:
        return prices
    if isinstance(raw, list):
        try:
            prices = [float(x) for x in raw if x is not None]
        except Exception:
            prices = []
    elif isinstance(raw, str):
        try:
            try:
                prices = [float(x) for x in json.loads(raw)]
            except json.JSONDecodeError:
                prices = [float(x) for x in ast.literal_eval(raw)]
        except Exception:
            prices = []
    return prices


def compute_mid_price(market: Dict[str, Any]) -> float | None:
    prices = _safe_get_prices(market)
    if not prices:
        return None
    # For binary markets, first price is typically the "Yes" probability
    if len(prices) >= 2:
        try:
            mid = float(prices[0])
            if 0.0 <= mid <= 1.0:
                return mid
        except Exception:
            pass
        return float(sum(prices) / len(prices))
    try:
        mid = float(prices[0])
        return mid if 0.0 <= mid <= 1.0 else None
    except Exception:
        return None


def get_volume(market: Dict[str, Any]) -> float:
    for key in ["volume24hr", "volumeClob", "volume24hrClob", "volume"]:
        v = market.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                continue
    return 0.0


def get_spread_cents(market: Dict[str, Any]) -> float | None:
    s = market.get("spread")
    if s is None:
        return None
    try:
        val = float(s)
        # Gamma often returns integer cents (e.g., 1 for 1c). Handle common cases:
        # - Integer small numbers: treat as cents
        # - Fractional <= 1.0: treat as probability and convert to cents
        # - 1 < val < 100: likely already cents
        if val.is_integer() and val <= 10:
            return val
        if val <= 1.0:
            return val * 100.0
        return val
    except Exception:
        return None


def extract_tags(market: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    events = market.get("events")
    if isinstance(events, list):
        for e in events:
            etags = e.get("tags") if isinstance(e, dict) else None
            if isinstance(etags, list):
                for t in etags:
                    if isinstance(t, dict):
                        for key in ("slug", "label"):
                            v = t.get(key)
                            if isinstance(v, str) and v:
                                tags.append(v.lower())
    # Fallback: look for top-level tags if present
    if isinstance(market.get("tags"), list):
        for t in market["tags"]:
            if isinstance(t, dict):
                for key in ("slug", "label"):
                    v = t.get(key)
                    if isinstance(v, str) and v:
                        tags.append(v.lower())
            elif isinstance(t, str):
                tags.append(t.lower())
    return list(dict.fromkeys(tags))  # dedupe, preserve order


def classify_market(
    market: Dict[str, Any],
    category_map: Dict[str, str] | None = None,
    keyword_rules: Dict[str, List[str]] | None = None,
) -> str:
    category_map = category_map or {}
    keyword_rules = keyword_rules or {}

    tags = extract_tags(market)
    for tag in tags:
        if tag in category_map:
            return category_map[tag]

    question = (market.get("question") or "").lower()
    ticker = (market.get("ticker") or "").lower()
    description = (market.get("description") or "").lower()
    text = f"{question} {ticker} {description}"

    for cat, words in keyword_rules.items():
        for w in words:
            try:
                if re.search(rf"\b{re.escape(w.lower())}\b", text):
                    return cat
            except Exception:
                # fallback to substring if regex fails
                if w.lower() in text:
                    return cat
    return "unknown"


def market_passes_filters(
    market: Dict[str, Any],
    cfg: Dict[str, Any],
    category: str | None = None,
) -> Tuple[bool, Dict[str, Any]]:
    ms = dict(cfg.get("market_selection", {}))
    # Apply per-category overrides
    if category and "per_category" in ms and isinstance(ms["per_category"], dict):
        overrides = ms["per_category"].get(category)
        if isinstance(overrides, dict):
            ms = {**ms, **{k: v for k, v in overrides.items() if v is not None}}

    volume = get_volume(market)
    mid = compute_mid_price(market)
    spread_c = get_spread_cents(market)
    tags = set(extract_tags(market))

    min_vol = float(ms.get("min_volume_24h", 0))
    max_spread_cents = ms.get("max_spread_cents")
    band = ms.get("mid_price_band", [0.0, 1.0])
    include_tags = set([t.lower() for t in ms.get("include_tags", [])])
    exclude_tags = set([t.lower() for t in ms.get("exclude_tags", [])])

    # Tag filters
    if include_tags:
        if tags.isdisjoint(include_tags):
            return False, {"reason": "include_tags", "tags": list(tags)}
    if exclude_tags and not tags.isdisjoint(exclude_tags):
        return False, {"reason": "exclude_tags", "tags": list(tags)}

    # Volume
    if volume < min_vol:
        return False, {"reason": "volume", "got": volume, "min": min_vol}

    # Mid band
    if mid is None or not (float(band[0]) <= mid <= float(band[1])):
        return False, {"reason": "mid_band", "mid": mid, "band": band}

    # Spread
    if max_spread_cents is not None and spread_c is not None:
        if spread_c > float(max_spread_cents):
            return False, {"reason": "spread", "spread_cents": spread_c}

    return True, {"volume": volume, "mid": mid, "spread_cents": spread_c}


def select_markets(cfg: Dict[str, Any], gamma: GammaMarketClient | None = None) -> List[Dict[str, Any]]:
    gamma = gamma or GammaMarketClient()
    limit = int(cfg.get("market_selection", {}).get("limit", 10))

    markets = gamma.get_current_markets(limit=200)
    category_map = cfg.get("market_selection", {}).get("category_map", {})
    keyword_rules = cfg.get("market_selection", {}).get("keyword_rules", {})

    selected: List[Dict[str, Any]] = []
    for m in markets:
        category = classify_market(m, category_map=category_map, keyword_rules=keyword_rules)
        ok, meta = market_passes_filters(m, cfg, category)
        if ok:
            m2 = dict(m)
            m2["category"] = category
            m2["mid"] = meta.get("mid")
            m2["_volume_eff"] = meta.get("volume", 0.0)
            selected.append(m2)

    selected.sort(key=lambda x: float(x.get("_volume_eff", 0.0)), reverse=True)
    return selected[:limit]
