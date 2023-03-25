from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
}

def update_state_trades(state):
    # Update timestamp of trades for logging
    time = state.timestamp
    for symbol in state.market_trades.keys():
        for trade in state.market_trades[symbol]:
            if trade.timestamp == time:
                trade.timestamp = time-100
    return

def log_orders(timestamp, orders):
    print("{} SENT_ORDERS {}".format(timestamp, json.dumps(orders, default=lambda o: o.__dict__, sort_keys=True)))

    return

class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        update_state_trades(state)
        print(state.toJSON())
        if result:
            log_orders(state.timestamp, result)

        return result
