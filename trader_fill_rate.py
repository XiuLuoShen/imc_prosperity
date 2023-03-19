from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
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
    curr_position = state.position.get(product, 0)
    max_short_order = -POSITION_LIMITS[product]-curr_position
    max_long_order = POSITION_LIMITS[product]-curr_position

    if len(order_depth.sell_orders) > 0:
        best_ask = min(order_depth.sell_orders.keys())
    else:
        return 

    if len(order_depth.buy_orders) != 0:
        best_bid = max(order_depth.buy_orders.keys())
    else:
        return
    
    spread = best_ask-best_bid
    # Buy Order
    post_px = best_bid
    if spread > 6:
        post_px += 3
    post_sz = min(4, max_long_order)
    orders.append(Order(product, post_px, post_sz))

    # Sell Order
    post_px = best_ask
    if spread > 6:
        post_px -= 3
    post_sz = max(-4, max_short_order)
    orders.append(Order(product, post_px, post_sz))

    return orders

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        print(state.toJSON())

        result = {}
        for product in state.order_depths.keys():
            # if product == 'PEARLS':
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
