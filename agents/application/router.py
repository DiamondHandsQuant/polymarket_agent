from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set, Tuple

import yaml

from agents.strategies.selection import market_passes_filters


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_markets_from_json(json_path: str) -> List[Dict[str, Any]]:
    if not json_path or not os.path.exists(json_path):
        return []
    with open(json_path, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def _load_yaml_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def _determine_source_json_path(source_config: str | None, explicit_json_path: str | None) -> str:
    if explicit_json_path:
        return explicit_json_path
    if source_config:
        cfg = _load_yaml_config(source_config)
        path_from_cfg = cfg.get("ops", {}).get("markets_json_path")
        if path_from_cfg:
            return path_from_cfg
    raise ValueError("markets_json_path is required via --markets-json-path or ops.markets_json_path in --source-config")


def _determine_output_path(bot_config: Dict[str, Any], explicit_output: str | None) -> str:
    if explicit_output:
        return explicit_output
    configured = bot_config.get("ops", {}).get("selected_markets_path")
    if configured:
        return configured
    raise ValueError("selected_markets_path must be provided via CLI or ops.selected_markets_path in the bot config")


def filter_cached_markets(markets: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for m in markets:
        ok, meta = market_passes_filters(m, cfg)
        if ok:
            m2 = dict(m)
            m2["mid"] = meta.get("mid")
            m2["_volume_eff"] = meta.get("volume", 0.0)
            selected.append(m2)
    # sort by effective volume descending if present
    selected.sort(key=lambda x: float(x.get("_volume_eff", 0.0)), reverse=True)
    return selected


def route_markets(
    source_config: str | None,
    markets_json_path: str | None,
    routes: List[Tuple[str, str, int | None, bool, str | None]],
) -> Dict[str, int]:
    """
    Route cached markets to multiple bots based on each bot's config.

    routes: list of tuples of (bot_name, bot_config_path, limit, allow_overlap, explicit_output_path)
    returns mapping of bot_name -> assigned_count
    """
    src_json = _determine_source_json_path(source_config, markets_json_path)
    markets = load_markets_from_json(src_json)

    assigned_ids: Set[str] = set()
    results: Dict[str, int] = {}

    for bot_name, bot_cfg_path, limit, allow_overlap, explicit_output in routes:
        bot_cfg = _load_yaml_config(bot_cfg_path)
        filtered = filter_cached_markets(markets, bot_cfg)

        # apply limit from argument or config; otherwise keep all
        if limit is None:
            ms = bot_cfg.get("market_selection", {})
            try:
                limit_val = int(ms.get("limit")) if ms.get("limit") is not None else None
            except Exception:
                limit_val = None
        else:
            limit_val = int(limit)

        out: List[Dict[str, Any]] = []
        for m in filtered:
            mid = m.get("mid")
            # ensure an id key exists as string
            mid_str = str(m.get("id", ""))
            if not allow_overlap and mid_str in assigned_ids:
                continue
            out.append(m)
            assigned_ids.add(mid_str)
            if limit_val is not None and len(out) >= limit_val:
                break

        out_path = _determine_output_path(bot_cfg, explicit_output)
        _ensure_parent(out_path)
        with open(out_path, "w") as f:
            json.dump(out, f)
        results[bot_name] = len(out)

    return results


