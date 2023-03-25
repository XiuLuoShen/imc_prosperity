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
        print(state.toJSON())

        result = {}
        for product in state.order_depths.keys():
            if product == 'PEARLS':
                order_depth: OrderDepth = state.order_depths[product]

                orders: list[Order] = []
                acceptable_price = 10000

                if len(order_depth.sell_orders) > 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = abs(order_depth.sell_orders[best_ask])

                    if best_ask < acceptable_price:
                        if abs(best_ask_volume) < 20:
                            orders.append(Order(product, best_ask, min(best_ask_volume+5, 20)))

                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = abs(order_depth.buy_orders[best_bid])
                    if best_bid > acceptable_price:
                        if abs(best_bid_volume) < 20:
                            orders.append(Order(product, best_bid, -min(best_bid_volume+5, 20)))

                result[product] = orders

        if result:
            log_orders(state.timestamp, result)
        return result
