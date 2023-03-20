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
        pos = min(pos, 5)
    elif pos < 0:
        pos = max(pos, -5)
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


def offset_bananas(fair_px: float, curr_pos: int):
    if np.abs(curr_pos) < 15:
        return fair_px
    else:
        return fair_px-0.2*(curr_pos-np.sign(curr_pos)*15)

def offset_pearls(fair_px: float, curr_pos: int):
    return fair_px-0.1*curr_pos
    
THEO_OFFSET_FUNC = {
    "PEARLS": offset_pearls,
    "BANANAS": offset_bananas,
}

def offset_fair_price(fair_px: float, product, curr_pos: int):
    return THEO_OFFSET_FUNC[product](fair_px, curr_pos)

def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    acceptable_price = compute_fair_price(order_depth)
    curr_pos = state.position.get(product, 0)
    acceptable_price = offset_fair_price(acceptable_price, product, curr_pos)

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_pos
    short_vol_avail = -POSITION_LIMITS[product]-curr_pos

    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
        bid_sizes = [order_depth.buy_orders[bid] for bid in bids]
    else:
        return
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
        ask_sizes = [order_depth.sell_orders[ask] for ask in asks]
    else:
        return
    
    active_buy, active_sell = False, False
    if asks[0] < acceptable_price and long_vol_avail:
        take_size = min(long_vol_avail, -ask_sizes[0]+1)
        long_vol_avail -= take_size
        active_buy = True
        orders.append(Order(product, asks[0], take_size))
    
    if bids[0] > acceptable_price and short_vol_avail:
        take_size = max(short_vol_avail, bid_sizes[0]-1)
        short_vol_avail += take_size
        active_sell = True
        orders.append(Order(product, bids[0], -take_size))

    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0] and curr_pos <= 15:
            post_px -= 2
        elif post_px-1 > bids[0] or (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 1

        post_sz = long_vol_avail # hard to get filled so send max order
        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 < asks[0] and curr_pos >= -15:
            post_px += 2
        elif post_px+1 < asks[0] or (post_px+1==asks[0] and ask_sizes[0] >= -2):
            post_px += 1

        post_sz = short_vol_avail # Hard to get filled so just yolo it
        orders.append(Order(product, post_px, post_sz))

    return orders

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        print(state.toJSON())

        result = {}
        for product in state.order_depths.keys():
            orders: list[Order] = []
            # if state.timestamp < 50000:
            alpha_trade(state, product, orders)
            # else:
                # flatten_position(state, product, orders)
            if orders:
                result[product] = orders

        if result:
            log_orders(state.timestamp, result)
        return result
