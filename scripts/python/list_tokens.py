import json
import os
import sys

from agents.polymarket.gamma import GammaMarketClient


def main() -> None:
    limit = int(os.environ.get("LIMIT", "5"))
    g = GammaMarketClient()
    markets = g.get_current_markets(limit=limit)
    out = []
    for m in markets:
        item = {
            "id": m.get("id"),
            "question": m.get("question"),
            "clobTokenIds": m.get("clobTokenIds"),
        }
        out.append(item)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()


