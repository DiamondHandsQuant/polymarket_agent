import typer
from devtools import pprint
import time

from agents.polymarket.polymarket import Polymarket
# Lazy imports for optional connectors moved into functions
# from agents.connectors.chroma import PolymarketRAG
# from agents.connectors.news import News
from agents.strategies.selection import select_markets
from agents.application.executor import Executor
from agents.application.creator import Creator

app = typer.Typer()
polymarket = Polymarket()
# newsapi_client = News()
# polymarket_rag = PolymarketRAG()


@app.command()
def get_all_markets(limit: int = 5, sort_by: str = "spread") -> None:
    """
    Query Polymarket's current active markets
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    markets = polymarket.get_all_markets()  # Now returns current markets by default
    markets = polymarket.filter_markets_for_trading(markets)
    if sort_by == "spread":
        markets = sorted(markets, key=lambda x: x.spread, reverse=True)
    elif sort_by == "volume":
        markets = sorted(markets, key=lambda x: x.volume, reverse=True)
    elif sort_by == "created":
        # Markets are already sorted by creation date from the API
        pass
    markets = markets[:limit]
    pprint(markets)


@app.command()
def get_relevant_news(keywords: str) -> None:
    """
    Use NewsAPI to query the internet
    """
    from agents.connectors.news import News
    newsapi_client = News()
    articles = newsapi_client.get_articles_for_cli_keywords(keywords)
    pprint(articles)


@app.command()
def get_current_markets(limit: int = 5) -> None:
    """
    Get the most recently created active markets
    """
    from agents.polymarket.gamma import GammaMarketClient
    gamma = GammaMarketClient()
    
    print(f"Fetching {limit} most recent active markets...")
    markets = gamma.get_current_markets(limit=limit)
    
    print(f"\n🔥 {len(markets)} Current Active Markets:")
    for i, market in enumerate(markets):
        print(f"\n{i+1}. {market.get('question', 'No question')}")
        print(f"   Created: {market.get('createdAt', 'Unknown')[:10]}")
        print(f"   Active: {market.get('active', 'N/A')}")
        volume = market.get('volume', 0)
        if volume:
            print(f"   Volume: ${float(volume):,.2f}")


@app.command()
def get_all_events(limit: int = 5, sort_by: str = "number_of_markets") -> None:
    """
    Query Polymarket's events
    """
    print(f"limit: int = {limit}, sort_by: str = {sort_by}")
    events = polymarket.get_all_events()
    events = polymarket.filter_events_for_trading(events)
    if sort_by == "number_of_markets":
        events = sorted(events, key=lambda x: len(x.markets), reverse=True)
    events = events[:limit]
    pprint(events)


@app.command()
def create_local_markets_rag(local_directory: str) -> None:
    """
    Create a local markets database for RAG
    """
    from agents.connectors.chroma import PolymarketRAG
    polymarket_rag = PolymarketRAG()
    polymarket_rag.create_local_markets_rag(local_directory=local_directory)


@app.command()
def query_local_markets_rag(vector_db_directory: str, query: str) -> None:
    """
    RAG over a local database of Polymarket's events
    """
    from agents.connectors.chroma import PolymarketRAG
    polymarket_rag = PolymarketRAG()
    response = polymarket_rag.query_local_markets_rag(
        local_directory=vector_db_directory, query=query
    )
    pprint(response)


@app.command()
def ask_superforecaster(event_title: str, market_question: str, outcome: str) -> None:
    """
    Ask a superforecaster about a trade
    """
    print(
        f"event: str = {event_title}, question: str = {market_question}, outcome (usually yes or no): str = {outcome}"
    )
    executor = Executor()
    response = executor.get_superforecast(
        event_title=event_title, market_question=market_question, outcome=outcome
    )
    print(f"Response:{response}")


@app.command()
def create_market() -> None:
    """
    Format a request to create a market on Polymarket
    """
    c = Creator()
    market_description = c.one_best_market()
    print(f"market_description: str = {market_description}")


@app.command()
def ask_llm(user_input: str) -> None:
    """
    Ask a question to the LLM and get a response.
    """
    executor = Executor()
    response = executor.get_llm_response(user_input)
    print(f"LLM Response: {response}")


@app.command()
def ask_polymarket_llm(user_input: str) -> None:
    """
    What types of markets do you want trade?
    """
    executor = Executor()
    response = executor.get_polymarket_llm(user_input=user_input)
    print(f"LLM + current markets&events response: {response}")


@app.command()
def refresh_markets(
    config: str = typer.Option("configs/option_seller.yaml"),
    limit: int = typer.Option(None),
    fetch_limit: int = typer.Option(None),
    min_volume_24h: float = typer.Option(None),
    skip_classify: bool = typer.Option(False),
    markets_json_path: str = typer.Option(None),
    markets_chroma_dir: str = typer.Option(None),
) -> None:
    """
    Refresh local markets cache and Chroma index using selection.select_markets.
    """
    import yaml
    from agents.connectors.chroma import PolymarketRAG

    with open(config, "r") as f:
        cfg = yaml.safe_load(f) or {}

    # apply overrides without hardcoding defaults
    if limit is not None:
        cfg.setdefault("market_selection", {})["limit"] = int(limit)
    if fetch_limit is not None:
        cfg.setdefault("market_selection", {})["fetch_limit"] = int(fetch_limit)
    if min_volume_24h is not None:
        cfg.setdefault("market_selection", {})["min_volume_24h"] = float(min_volume_24h)
    if skip_classify:
        cfg.setdefault("market_selection", {})["classify"] = False

    markets = select_markets(cfg)

    # Determine output paths from config if provided; otherwise use conventional paths
    # prefer CLI args if provided, else config values, else conventional paths
    markets_json = markets_json_path or cfg.get("ops", {}).get("markets_json_path") or "local_db_markets/markets.json"
    chroma_dir = markets_chroma_dir or cfg.get("ops", {}).get("markets_chroma_dir") or "local_db_markets/chroma"

    rag = PolymarketRAG()
    rag.persist_markets(markets=markets, json_file_path=markets_json, vector_db_directory=chroma_dir)
    print(f"Persisted {len(markets)} markets to {markets_json} and {chroma_dir}")


@app.command()
def route_markets(
    source_config: str = typer.Option("configs/option_seller.yaml"),
    markets_json_path: str = typer.Option(None),
    option_seller_config: str = typer.Option("configs/option_seller.yaml"),
    market_maker_config: str = typer.Option("configs/market_maker.yaml"),
    risk_manager_config: str = typer.Option("configs/risk.yaml"),
    option_seller_limit: int = typer.Option(None),
    market_maker_limit: int = typer.Option(None),
    risk_manager_limit: int = typer.Option(None),
    allow_overlap: bool = typer.Option(False),
    option_seller_output: str = typer.Option(None),
    market_maker_output: str = typer.Option(None),
    risk_manager_output: str = typer.Option(None),
) -> None:
    """
    Route cached markets to per-bot selections using config-driven filters.
    """
    from agents.application.router import route_markets as route

    routes = [
        ("option_seller", option_seller_config, option_seller_limit, allow_overlap, option_seller_output),
        ("market_maker", market_maker_config, market_maker_limit, allow_overlap, market_maker_output),
        ("risk_manager", risk_manager_config, risk_manager_limit, allow_overlap, risk_manager_output),
    ]

    results = route(
        source_config=source_config,
        markets_json_path=markets_json_path,
        routes=routes,
    )

    pprint(results)


# New commands for automated strategies
@app.command()
def run_option_seller(config: str = typer.Option("configs/option_seller.yaml"), duration: int = typer.Option(5)) -> None:
    """Run Option Seller bot (dry-run by default)."""
    from agents.strategies.option_seller import OptionSellerBot
    bot = OptionSellerBot(config)
    bot.start()
    time_end = time.time() + duration
    while time.time() < time_end:
        time.sleep(0.5)
    bot.stop()


@app.command()
def run_market_maker(config: str = typer.Option("configs/market_maker.yaml"), duration: int = typer.Option(5)) -> None:
    """Run Market Maker bot (dry-run by default)."""
    from agents.strategies.market_maker import MarketMakerBot
    bot = MarketMakerBot(config)
    bot.start()
    time_end = time.time() + duration
    while time.time() < time_end:
        time.sleep(0.5)
    bot.stop()


@app.command()
def run_risk_manager(config: str = typer.Option("configs/risk.yaml"), duration: int = typer.Option(5)) -> None:
    """Run Risk Manager controller (dry-run by default)."""
    from agents.strategies.risk import RiskManagerBot
    bot = RiskManagerBot(config)
    bot.start()
    time_end = time.time() + duration
    while time.time() < time_end:
        time.sleep(0.5)
    bot.stop()


if __name__ == "__main__":
    app()
