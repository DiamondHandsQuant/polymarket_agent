from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket

import shutil


class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def pre_trade_logic(self) -> None:
        self.clear_local_dbs()

    def clear_local_dbs(self) -> None:
        try:
            shutil.rmtree("local_db_events")
        except:
            pass
        try:
            shutil.rmtree("local_db_markets")
        except:
            pass

    def one_best_trade(self) -> None:
        """

        one_best_trade is a strategy that evaluates all events, markets, and orderbooks

        leverages all available information sources accessible to the autonomous agent

        then executes that trade without any human intervention

        """
        try:
            self.pre_trade_logic()

            # Use current markets instead of stale events
            current_markets = self.gamma.get_current_markets(limit=50)
            print(f"1. FOUND {len(current_markets)} CURRENT MARKETS")

            # Convert to SimpleEvent objects for compatibility with existing RAG system
            from agents.utils.objects import SimpleEvent
            events = []
            for i, market in enumerate(current_markets):
                # Create proper SimpleEvent objects from market data
                event = SimpleEvent(
                    id=market.get('id', i),
                    ticker=market.get('ticker', f"MARKET_{i}"),
                    slug=market.get('slug', f"market-{i}"),
                    title=market.get('question', 'Unknown Market'),
                    description=market.get('description', market.get('question', 'No description')),
                    end=market.get('endDate', market.get('end_date_iso', '2025-12-31')),
                    active=market.get('active', True),
                    closed=market.get('closed', False),
                    archived=market.get('archived', False),
                    restricted=market.get('restricted', False),
                    new=market.get('new', False),
                    featured=market.get('featured', False),
                    markets=str(market.get('id', i))  # Store market ID as string
                )
                events.append(event)

            filtered_events = self.agent.filter_events_with_rag(events)
            print(f"2. FILTERED {len(filtered_events)} EVENTS")

            # Map filtered events back to markets (since we already have current_markets)
            if filtered_events:
                # Extract market IDs from filtered events
                filtered_market_ids = []
                for event_tuple in filtered_events:
                    if hasattr(event_tuple[0], 'metadata') and 'markets' in event_tuple[0].metadata:
                        market_id = event_tuple[0].metadata['markets']
                        filtered_market_ids.append(market_id)
                    elif hasattr(event_tuple[0], 'markets'):
                        market_id = event_tuple[0].markets
                        filtered_market_ids.append(market_id)
                
                # Filter current_markets to only include the RAG-selected ones
                markets = [m for m in current_markets if str(m.get('id', '')) in filtered_market_ids]
                if not markets:
                    # Fallback: use first few current markets if filtering failed
                    markets = current_markets[:5]
            else:
                # Fallback: use first few current markets if no events were filtered
                markets = current_markets[:5]
            print()
            print(f"3. FOUND {len(markets)} MARKETS")

            print()
            filtered_markets = self.agent.filter_markets(markets)
            print(f"4. FILTERED {len(filtered_markets)} MARKETS")

            market = filtered_markets[0]
            best_trade = self.agent.source_best_trade(market)
            print(f"5. CALCULATED TRADE {best_trade}")

            amount = self.agent.format_trade_prompt_for_execution(best_trade)
            # Please refer to TOS before uncommenting: polymarket.com/tos
            # trade = self.polymarket.execute_market_order(market, amount)
            # print(f"6. TRADED {trade}")

        except Exception as e:
            print(f"Error {e} \n \n Retrying")
            self.one_best_trade()

    def maintain_positions(self):
        pass

    def incentive_farm(self):
        pass


if __name__ == "__main__":
    t = Trader()
    t.one_best_trade()
