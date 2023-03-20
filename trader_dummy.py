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

        for product in state.order_depths.keys():

            # Check if the current product is the 'PEARLS' product, only then run the order logic
            if product == 'PEARLS':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for PEARLS
                order_depth: OrderDepth = state.order_depths[product]
                print(order_depth.buy_orders.keys())
                print(order_depth.sell_orders.keys())


        print(state.toJSON())
        if result:
            log_orders(state.timestamp, result)

        return result
