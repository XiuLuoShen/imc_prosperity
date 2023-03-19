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

def compute_fair_price(order_depth: OrderDepth) -> float:
    """ Compute size weighted price using orders in the state
    """
    total_notional = 0
    total_size = 0
    for px in order_depth.buy_orders.keys():
        sz = np.abs(order_depth.buy_orders[px])
        total_size += sz
        total_notional += float(px)*sz
    
    for px in order_depth.sell_orders.keys():
        sz = np.abs(order_depth.sell_orders[px])
        total_size += sz
        total_notional += float(px)*sz

    return total_notional/total_size


def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    acceptable_price = compute_fair_price(order_depth)
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

    
    # Buy Order
    post_px = int(np.floor(acceptable_price))-1
    orders.append(Order(product, post_px, max_long_order))

    # Sell Order
    post_px = int(np.ceil(acceptable_price))+1
    orders.append(Order(product, post_px, max_short_order))

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
