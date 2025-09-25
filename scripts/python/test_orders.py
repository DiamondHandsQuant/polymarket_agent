import json
import os
import sys
from typing import Any, Dict

import yaml

from agents.strategies.orders import OrderContext, place_limit, cancel
from agents.polymarket.polymarket import Polymarket


class DummyPolymarket:
    def execute_order(self, price, size, side, token_id) -> str:  # pragma: no cover
        return "DUMMY_EXCHANGE_ID"

    def get_orderbook_price(self, token_id: str) -> float:  # pragma: no cover
        return 0.5


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val


def main() -> None:
    config_path = _require_env("CONFIG_PATH")
    token_id = _require_env("TOKEN_ID")
    side = _require_env("SIDE")
    price_str = _require_env("PRICE")
    size_str = _require_env("SIZE")

    try:
        with open(config_path, "r") as f:
            config: Dict[str, Any] = yaml.safe_load(f) or {}
    except Exception as err:
        print(f"Failed to load CONFIG_PATH: {err}", file=sys.stderr)
        sys.exit(1)

    ops = config.get("ops", {})
    state_dir = ops.get("state_dir")
    log_path = ops.get("log_path")

    real = os.environ.get("REAL", "0") == "1"
    poly = Polymarket() if real else DummyPolymarket()

    ctx = OrderContext(
        polymarket=poly,
        config=config,
        state_dir=state_dir,
        log_path=log_path,
    )

    # Will run dry or live based on config ops.dry_run
    order_id = place_limit(
        price=float(price_str),
        size=float(size_str),
        side=side,
        token_id=token_id,
        ctx=ctx,
    )

    print(json.dumps({"placed_order_id": order_id}))

    # Exercise cancel in dry-run
    cancel(order_id, ctx)


if __name__ == "__main__":
    main()


