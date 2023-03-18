from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json


POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
}

FAIR_PRICE = {
    "PEARLS": 10000
}

def log_orders(timestamp, orders):
    print("{} SENT_ORDERS {}".format(timestamp, json.dumps(orders, default=lambda o: o.__dict__, sort_keys=True)))

    return

def flatten_position(state: TradingState, product, orders: Dict[str, List[Order]]):
    pos = state.position[product]
    if pos == 0:
        return
    if pos > 0:
        px = max(state.order_depths[product].buy_orders.keys())
    elif pos < 0:
        px = min(state.order_depths[product].sell_orders.keys())
    orders.append(Order(product, px, -pos))

    return

def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    acceptable_price = FAIR_PRICE[product]

    if len(order_depth.sell_orders) > 0:
        best_ask = min(order_depth.sell_orders.keys())
        best_ask_volume = order_depth.sell_orders[best_ask]

        if best_ask < acceptable_price:
            orders.append(Order(product, best_ask, -best_ask_volume))

    if len(order_depth.buy_orders) != 0:
        best_bid = max(order_depth.buy_orders.keys())
        best_bid_volume = order_depth.buy_orders[best_bid]
        if best_bid > acceptable_price:
            orders.append(Order(product, best_bid, -best_bid_volume))

    return orders

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        print(state.toJSON())

        result = {}
        for product in state.order_depths.keys():
            if product == 'PEARLS':
                orders: list[Order] = []
                if state.timestamp < 50000:
                    alpha_trade(state, product, orders)
                else:
                    flatten_position(state, product, orders)
                if orders:
                    result[product] = orders

        if result:
            log_orders(state.timestamp, result)
        return result
