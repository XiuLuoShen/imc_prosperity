from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
    # "COCONUTS": 600,
    # "PINA_COLADAS": 300,
}

class AlgoOrder:
    def __init__(self, symbol: str, price: int, side: str, quantity: int, note: str = 'None'):
        self.symbol = symbol
        self.price = price
        if side == 'BUY':
            self.side = 1
        elif side == 'SELL':
            self.side = -1
        self.quantity = quantity
        self.note = note

    def create_market_order(self):
        """ Create an order to send
        """
        if self.side == -1:
            qty = -1*self.quantity
        else:
            qty = self.quantity
        return Order(self.symbol, self.price, qty)

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


def compute_fair_price(bids, bid_sizes, asks, ask_sizes) -> float:
    """ Compute size weighted price using orders in the state
    """
    total_notional = 0
    total_size = 0
    for i in range(len(bids)):
        total_size += bid_sizes[i]
        total_notional += float(bids[i]*bid_sizes[i])
    
    for i in range(len(asks)):
        total_size += ask_sizes[i]
        total_notional += float(asks[i]*ask_sizes[i])

    return total_notional/total_size


def offset_bananas(fair_px: float, curr_pos: int):
    # return fair_px-0.075*curr_pos
    if np.abs(curr_pos) <= 5:
        return fair_px
    else:
        return fair_px-0.075*(curr_pos-np.sign(curr_pos)*5)

def offset_pearls(fair_px: float, curr_pos: int):
    return fair_px-0.025*curr_pos
    
THEO_OFFSET_FUNC = {
    "PEARLS": offset_pearls,
    "BANANAS": offset_bananas,
}

def offset_fair_price(fair_px: float, product, curr_pos: int):
    return THEO_OFFSET_FUNC[product](fair_px, curr_pos)


def passive_trades_bananas(state: TradingState, product, orders: List[Order], fair_buy_px, fair_sell_px, curr_pos: int, long_vol_avail: int, short_vol_avail: int, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell):
    best_bid = bids[active_sell] if len(bids) > active_sell else bids[0]-1
    best_bid_vol = bid_sizes[active_sell] if len(bids) > active_sell else long_vol_avail

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[active_buy]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = 20

    if long_vol_avail > 0:
        post_px = int(np.floor(fair_buy_px))
        posted = False
        for dx in [4, 3, 2, 1]:
            if post_px - dx > best_bid:
                post_sz = min(long_vol_avail, max_post_sz)
                long_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px-dx, 'BUY', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted and curr_pos <= 18:
            post_sz = min(long_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'BUY', post_sz, note=f'P0'))
    # Sell Orders
    if short_vol_avail > 0:
        post_px = int(np.ceil(fair_sell_px))
        posted = False
        for dx in [4, 3, 2, 1]:
            if post_px + dx < best_ask:
                post_sz = min(short_vol_avail, max_post_sz)
                short_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px+dx, 'SELL', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted and curr_pos >= -18:
            post_sz = min(short_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note=f'P0'))

    return

def passive_trades_pearls(state: TradingState, product, orders: List[Order], fair_buy_px, fair_sell_px, curr_pos: int, long_vol_avail: int, short_vol_avail: int, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell):
    # Adjust top of quote if we take it out
    best_bid = bids[active_sell] if len(bids) > active_sell else bids[0]-1
    best_bid_vol = bid_sizes[active_sell] if len(bids) > active_sell else long_vol_avail

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[active_buy]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = 12
    if long_vol_avail > 0:
        post_px = int(np.floor(fair_buy_px))
        posted = False
        for dx in [4, 3, 2, 1]:
            if post_px - dx > best_bid:
                post_sz = min(long_vol_avail, max_post_sz)
                long_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px-dx, 'BUY', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted and curr_pos <= 18:
            post_sz = min(long_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'BUY', post_sz, note=f'P0'))
    # Sell Orders
    if short_vol_avail > 0:
        post_px = int(np.ceil(fair_sell_px))
        posted = False
        for dx in [4, 3, 2, 1]:
            if post_px + dx < best_ask:
                post_sz = min(short_vol_avail, max_post_sz)
                short_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px+dx, 'SELL', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted and curr_pos >= -18:
            post_sz = min(short_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note=f'P0'))

    return

def alpha_trade(state: TradingState, product):
    order_depth: OrderDepth = state.order_depths[product]
    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
        bid_sizes = [order_depth.buy_orders[bid] for bid in bids]
    else:
        return []
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
        ask_sizes = [abs(order_depth.sell_orders[ask]) for ask in asks]
    else:
        return []
    
    orders = []

    curr_pos = state.position.get(product, 0)
    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(fair_px, product, curr_pos)
    fair_buy_px = fair_sell_px = fair_px

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_pos
    short_vol_avail = abs(-POSITION_LIMITS[product]-curr_pos)

    mid = (bids[0] + asks[0])/2
    spread = asks[0]-bids[0]
    active_buy, active_sell = 0, 0
    # for i in range(len(asks)):
    i = 0
    if asks[i] < fair_buy_px and long_vol_avail:
        take_size = min(long_vol_avail, ask_sizes[i])
        long_vol_avail -= take_size
        ask_sizes[i] -= take_size
        curr_pos += take_size # Adjust position for posting
        active_buy = i+1   
        orders.append(AlgoOrder(product, asks[i], 'BUY', take_size, note=f'X_{i}'))
    # else:
    #     break

    # for i in range(len(bids)):
    if bids[i] > fair_sell_px and short_vol_avail:
        take_size = min(short_vol_avail, bid_sizes[i])
        short_vol_avail -= take_size
        bid_sizes[i] -= take_size
        curr_pos -= take_size # Adjust position for posting
        active_sell = i+1
        orders.append(AlgoOrder(product, bids[i], 'SELL', take_size, note=f'X_{i}'))
        # else:
        #     break
    
    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(fair_px, product, curr_pos)
    fair_buy_px = fair_sell_px = fair_px

    if product == 'BANANAS':
        passive_trades_bananas(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)
    if product == 'PEARLS':
        passive_trades_pearls(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)   

    return orders

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        for product in state.order_depths.keys():
            if product in POSITION_LIMITS:
                orders: list[Order] = alpha_trade(state, product)
                if orders:
                    result[product] = orders

        update_state_trades(state)
        print(state.toJSON())
        if result:
            log_orders(state.timestamp, result)

        if result:
            for product in result.keys():
                orders = [o.create_market_order() for o in result[product]]
                result[product] = orders

        return result
