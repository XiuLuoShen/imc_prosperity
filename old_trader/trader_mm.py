from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
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

def log_state(state):
    timestamp = state.timestamp
    print("{} ORDER_DEPTHS {}".format(timestamp, json.dumps(state.order_depths, default=lambda o: o.__dict__, sort_keys=True)))
    print("{} MARKET_TRADES {}".format(timestamp, json.dumps(state.market_trades, default=lambda o: o.__dict__, sort_keys=True)))
    print("{} OWN_TRADES {}".format(timestamp, json.dumps(state.own_trades, default=lambda o: o.__dict__, sort_keys=True)))
    print("{} POSITION {}".format(timestamp, json.dumps(state.position, default=lambda o: o.__dict__, sort_keys=True)))

    # print("{} OBSERVATIONS {}".format(timestamp, json.dumps(state.observations, default=lambda o: o.__dict__, sort_keys=True)))

    return

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
    if np.abs(curr_pos) <= 15:
        return fair_px
    else:
        return fair_px-0.2*(curr_pos-np.sign(curr_pos)*15)

def offset_pearls(fair_px: float, curr_pos: int):
    return fair_px-0.025*curr_pos
    
THEO_OFFSET_FUNC = {
    "PEARLS": offset_pearls,
    "BANANAS": offset_bananas,
}

def offset_fair_price(fair_px: float, product, curr_pos: int):
    return THEO_OFFSET_FUNC[product](fair_px, curr_pos)

def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    fair_price = compute_fair_price(order_depth)
    curr_pos = state.position.get(product, 0)
    
    acceptable_price = offset_fair_price(fair_price, product, curr_pos)

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_pos
    short_vol_avail = abs(-POSITION_LIMITS[product]-curr_pos)

    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
        bid_sizes = [order_depth.buy_orders[bid] for bid in bids]
    else:
        return
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
        ask_sizes = [abs(order_depth.sell_orders[ask]) for ask in asks]
    else:
        return
    
    mid = (bids[0] + asks[0])/2
    spread = asks[0]-bids[0]
    active_buy, active_sell = False, False
    for i in range(len(asks)):
        if asks[i] < acceptable_price and long_vol_avail:
            take_size = min(long_vol_avail, ask_sizes[i])
            long_vol_avail -= take_size
            active_buy = True            
            orders.append(AlgoOrder(product, asks[i], 'BUY', take_size, note=f'X_{i}'))
        else:
            break

    for i in range(len(bids)):
        if bids[i] > acceptable_price and short_vol_avail:
            take_size = min(short_vol_avail, bid_sizes[i])
            short_vol_avail -= take_size
            active_sell = True
            orders.append(AlgoOrder(product, bids[i], 'SELL', take_size, note=f'X_{i}'))
        else:
            break

    if long_vol_avail > 0:
        post_px = int(np.floor(acceptable_price))
        if post_px-4 > bids[0] and curr_pos >= -19:
            post_sz = long_vol_avail
            long_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px-4, 'BUY', post_sz, note='P4'))
        elif post_px-3 > bids[0] and curr_pos >= -19:
            post_sz = long_vol_avail
            long_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px-3, 'BUY', post_sz, note='P3'))
        elif post_px-2 > bids[0] and curr_pos >= -19:
            post_sz = long_vol_avail
            long_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px-2, 'BUY', post_sz, note='P2'))
        elif (post_px-1 > bids[0]):
            post_sz = long_vol_avail
            long_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px-1, 'BUY', post_sz, note='P1'))
        elif (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_sz = min(bid_sizes[0], long_vol_avail)
            long_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px, 'BUY', post_sz, note='P1_2'))
            if long_vol_avail:
                post_sz = long_vol_avail
                long_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px-1, 'BUY', post_sz, note='P1_1'))
        elif curr_pos <= 5:
            post_sz = long_vol_avail # hard to get filled so send max order
            orders.append(AlgoOrder(product, post_px, 'BUY', post_sz, note='P0'))
        
    # Sell Orders
    if short_vol_avail:
        post_px = int(np.ceil(acceptable_price))
        if post_px+4 < asks[0] and curr_pos <= 19:
            post_sz = short_vol_avail
            short_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px+4, 'SELL', post_sz, note='P4'))
        elif post_px+3 < asks[0] and curr_pos <= 19:
            post_sz = short_vol_avail
            short_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px+3, 'SELL', post_sz, note='P3'))
        elif post_px+2 < asks[0] and curr_pos <= 19:
            post_sz = short_vol_avail
            short_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px+2, 'SELL', post_sz, note='P2'))
        elif (post_px+1 < asks[0]) and curr_pos > 0:
            post_sz = short_vol_avail
            short_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px+1, 'SELL', post_sz, note='P1'))
        elif (post_px+1 == asks[0] and ask_sizes[0] <= 2):
            post_sz = min(ask_sizes[0], short_vol_avail)
            short_vol_avail -= post_sz
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note='P1_2'))
            if short_vol_avail:
                post_sz = short_vol_avail
                short_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px+1, 'SELL', post_sz, note='P1_1'))
        elif curr_pos >= -5:
            post_sz = short_vol_avail # Hard to get filled so just yolo it
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note='P0'))

    return orders

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        for product in state.order_depths.keys():
            orders: list[Order] = []
            # if state.timestamp < 50000:
            alpha_trade(state, product, orders)
            # else:
                # flatten_position(state, product, orders)
            if orders:
                result[product] = orders

        update_state_trades(state)
        print(state.toJSON())
        # log_state(state)

        if result:
            log_orders(state.timestamp, result)
            for product in result.keys():
                orders = [o.create_market_order() for o in result[product]]
                result[product] = orders

        return result
