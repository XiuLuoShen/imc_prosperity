from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
}

def log_orders(timestamp, orders):
    print("{} SENT_ORDERS {}".format(timestamp, json.dumps(orders, default=lambda o: o.__dict__, sort_keys=True)))

    return

class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        print(state.toJSON())
        log_orders(state.timestamp, result)

        return result
