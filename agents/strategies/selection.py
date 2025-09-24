from __future__ import annotations

import ast
import json
import os
import time
from typing import Any, Dict, List, Tuple

from agents.polymarket.gamma import GammaMarketClient
from agents.application.executor import Executor
from agents.application.prompts import Prompter


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
        # Common formats: integer cents (e.g., 1), or fraction (e.g., 0.02)
        if val.is_integer() and val <= 10:
            return val
        if val <= 1.0:
            return val * 100.0
        return val
    except Exception:
        return None


# ---------- LLM classification with caching ----------

def _load_cache(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(path: str, data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _cache_key(market: Dict[str, Any]) -> str:
    q = (market.get("question") or "").strip()
    mid = str(compute_mid_price(market) or "")
    return f"{market.get('id','')}::{q}::{mid}"


def _cache_fresh(entry: Dict[str, Any], ttl_hours: int) -> bool:
    try:
        ts = float(entry.get("ts", 0))
        return (time.time() - ts) <= ttl_hours * 3600
    except Exception:
        return False


def classify_market_llm(market: Dict[str, Any], cache: Dict[str, Any], ttl_hours: int, executor: Executor, prompter: Prompter) -> str:
    key = _cache_key(market)
    if key in cache and _cache_fresh(cache[key], ttl_hours):
        return cache[key].get("category", "other")

    question = (market.get("question") or "").strip()
    description = (market.get("description") or "").strip()
    slug = (market.get("slug") or "").strip()

    prompt = prompter.classify_market_category(question=question, description=description, slug=slug)
    result = executor.llm.invoke(prompt)
    cat = "other"
    try:
        data = json.loads(result.content)
        c = (data or {}).get("category")
        if isinstance(c, str) and c:
            cat = c.lower()
    except Exception:
        cat = "other"

    cache[key] = {"category": cat, "ts": time.time()}
    return cat


# ---------- Filters and selection ----------

def market_passes_filters(
    market: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    ms = dict(cfg.get("market_selection", {}))

    volume = get_volume(market)
    mid = compute_mid_price(market)
    spread_c = get_spread_cents(market)

    min_vol = float(ms.get("min_volume_24h", 0))
    max_spread_cents = ms.get("max_spread_cents")
    band = ms.get("mid_price_band", [0.0, 1.0])

    if volume < min_vol:
        return False, {"reason": "volume", "got": volume, "min": min_vol}
    if mid is None or not (float(band[0]) <= mid <= float(band[1])):
        return False, {"reason": "mid_band", "mid": mid, "band": band}
    if max_spread_cents is not None and spread_c is not None:
        if spread_c > float(max_spread_cents):
            return False, {"reason": "spread", "spread_cents": spread_c}

    return True, {"volume": volume, "mid": mid, "spread_cents": spread_c}


def select_markets(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    ms = cfg.get("market_selection", {})
    limit = int(ms.get("limit", 10))

    gamma = GammaMarketClient()
    markets = gamma.get_current_markets(limit=200)

    selected: List[Dict[str, Any]] = []

    exec_obj = Executor()
    prompter = Prompter()
    cache_path = ms.get("cache_path", "local_state/category_cache.json")
    cache_ttl = int(ms.get("cache_ttl_hours", 24))
    cache = _load_cache(cache_path)

    for m in markets:
        category = classify_market_llm(m, cache, cache_ttl, exec_obj, prompter)
        ok, meta = market_passes_filters(m, cfg)
        if ok:
            m2 = dict(m)
            m2["category"] = category
            m2["mid"] = meta.get("mid")
            m2["_volume_eff"] = meta.get("volume", 0.0)
            selected.append(m2)

    _save_cache(cache_path, cache)

    selected.sort(key=lambda x: float(x.get("_volume_eff", 0.0)), reverse=True)
    return selected[:limit]
