from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
}

MAX_POST_SIZE = {
    "BANANAS": 20,
    "PEARLS": 12,
    "COCONUTS": 39,
    "PINA_COLADAS": 19,
}

PAIRS = {
    'COCONUTS': 'PINA_COLADAS',
    'PINA_COLADAS': 'COCONUTS'
}

def reset_state():
    print("HARD RESET OF GLOBAL VARIABLES OCCURED")
    global trader_state
    trader_state = {
        'PAIR1': {'RAW_SIGNALS':[],
                'EMA_1': 0,
                'EMA_2': 0,
                'LAST_TIME': 0,
                'PAST_SIGNALS': [],
                }
    }
    return


trader_state = {
    'PAIR1': {'RAW_SIGNALS':[],
              'EMA_1': 0,
              'EMA_2': 0,
              'LAST_TIME': 0,
              'PAST_SIGNALS': [],
              }
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
        return Order(self.symbol, self.price, int(qty))

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

def offset_coconuts(fair_px: float, curr_pos: int, pina_pos: int):
    return fair_px-curr_pos*0.005-pina_pos*0.005
    
def offset_pina_coladas(fair_px: float, curr_pos: int, coco_pos: int):
    return fair_px-curr_pos*0.01-coco_pos*0.01/4

THEO_OFFSET_FUNC = {
    "PEARLS": offset_pearls,
    "BANANAS": offset_bananas,
    "COCONUTS": offset_coconuts,
    "PINA_COLADAS": offset_pina_coladas,
}

def offset_fair_price(product, *args):
    return THEO_OFFSET_FUNC[product](*args)


def passive_trades_bananas(state: TradingState, product, orders: List[Order], fair_buy_px, fair_sell_px, curr_pos: int, long_vol_avail: int, short_vol_avail: int, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell):
    best_bid = bids[active_sell] if len(bids) > active_sell else bids[0]-1
    best_bid_vol = bid_sizes[active_sell] if len(bids) > active_sell else long_vol_avail

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[0]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = MAX_POST_SIZE['BANANAS']

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

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[0]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = MAX_POST_SIZE['PEARLS']
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


def passive_trades_general(state: TradingState, product, orders: List[Order], fair_buy_px, fair_sell_px, curr_pos: int, long_vol_avail: int, short_vol_avail: int, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell):
    # Adjust top of quote if we take it out
    best_bid = bids[active_sell] if len(bids) > active_sell else bids[0]-1
    best_bid_vol = bid_sizes[active_sell] if len(bids) > active_sell else long_vol_avail

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[0]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = MAX_POST_SIZE[product]
    if long_vol_avail > 0:
        post_px = int(np.floor(fair_buy_px))
        posted = False
        for dx in [2, 1]:
            if post_px - dx > best_bid:
                post_sz = min(long_vol_avail, max_post_sz)
                long_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px-dx, 'BUY', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted:
            post_sz = min(long_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'BUY', post_sz, note=f'P0'))
    # Sell Orders
    if short_vol_avail > 0:
        post_px = int(np.ceil(fair_sell_px))
        posted = False
        for dx in [2, 1]:
            if post_px + dx < best_ask:
                post_sz = min(short_vol_avail, max_post_sz)
                short_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px+dx, 'SELL', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted:
            post_sz = min(short_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note=f'P0'))

    return

def get_bids_asks(order_depth):
    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
        bid_sizes = [order_depth.buy_orders[bid] for bid in bids]
    else:
        return False, [], [], [], []
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
        ask_sizes = [abs(order_depth.sell_orders[ask]) for ask in asks]
    else:
        return False, [], [], [], []
    return True, bids, asks, bid_sizes, ask_sizes

def alpha_trade(state: TradingState, product):
    order_depth: OrderDepth = state.order_depths[product]
    valid, bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth)
    if not valid:
        return []
    
    orders = []

    curr_pos = state.position.get(product, 0)
    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(product, fair_px, curr_pos)
    fair_buy_px = fair_sell_px = fair_px

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_pos
    short_vol_avail = abs(-POSITION_LIMITS[product]-curr_pos)

    mid = (bids[0] + asks[0])/2
    spread = asks[0]-bids[0]
    active_buy, active_sell = 0, 0

    i = 0
    if asks[i] < fair_buy_px and long_vol_avail:
        take_size = min(long_vol_avail, ask_sizes[i])
        long_vol_avail -= take_size
        ask_sizes[i] -= take_size
        curr_pos += take_size # Adjust position for posting
        active_buy = i+1   
        orders.append(AlgoOrder(product, asks[i], 'BUY', take_size, note=f'X_{i}'))

    if bids[i] > fair_sell_px and short_vol_avail:
        take_size = min(short_vol_avail, bid_sizes[i])
        short_vol_avail -= take_size
        bid_sizes[i] -= take_size
        curr_pos -= take_size # Adjust position for posting
        active_sell = i+1
        orders.append(AlgoOrder(product, bids[i], 'SELL', take_size, note=f'X_{i}'))
    
    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(product, fair_px, curr_pos)
    fair_buy_px = fair_sell_px = fair_px

    if product == 'BANANAS':
        passive_trades_bananas(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)
    elif product == 'PEARLS':
        passive_trades_pearls(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)

    return orders


def ema_calculate(new_entry, prev_ema, alpha):
    return new_entry*alpha+prev_ema*(1-alpha)

def target_pairs_position(z_score, past_zscore, curr_pos):
    # Target position for pina coladas
    entry = 1.75
    if z_score >= entry:
        target_pos = np.floor((z_score-entry)*100)
        return target_pos, 'enter_long'
    if z_score <= -entry:
        target_pos = np.ceil((z_score+entry)*100)
        return target_pos, 'enter_short'

    exit_active = 0.75 # other side
    if curr_pos > 0 and z_score < -exit_active:
        return 0, 'exit_active'
    elif curr_pos > 0 and z_score < 0:
        return 0, 'exit_passive'
    
    if curr_pos < 0 and z_score > exit_active:
        return 0, 'exit_active'
    elif curr_pos < 0 and z_score > 0:
        return 0, 'exit_passive'
    
    return curr_pos, 'NO_TRADE'


def alpha_trade_pair1(state: TradingState):
    # Active only strategy for now
    sym1 = 'COCONUTS'
    sym2 = 'PINA_COLADAS'
    od1 = state.order_depths[sym1]
    od2 = state.order_depths[sym2]

    valid, bids1, asks1, bid_sizes1, ask_sizes1 = get_bids_asks(od1)
    if not valid:
        return []
    valid, bids2, asks2, bid_sizes2, ask_sizes2 = get_bids_asks(od2)
    if not valid:
        return []

    mid1 = (bids1[0] + asks1[0])/2
    mid2 = (bids2[0] + asks2[0])/2
    raw_signal = 100*(mid2/mid1-15/8)

    global trader_state
    if state.timestamp - trader_state['PAIR1']['LAST_TIME'] > 300:
        reset_state()
    
    trader_state['PAIR1']['LAST_TIME'] = state.timestamp
    trader_state['PAIR1']['RAW_SIGNALS'].append(raw_signal)
    win1 = 20
    win2 = 100
    if len(trader_state['PAIR1']['RAW_SIGNALS']) < win1:
        trader_state['PAIR1']['EMA_1'] = np.mean(trader_state['PAIR1']['RAW_SIGNALS'])
        trader_state['PAIR1']['EMA_2'] = np.mean(trader_state['PAIR1']['RAW_SIGNALS'])
    elif len(trader_state['PAIR1']['RAW_SIGNALS']) < win2:
        trader_state['PAIR1']['EMA_1'] = ema_calculate(raw_signal,trader_state['PAIR1']['EMA_1'], 1/win1)
        trader_state['PAIR1']['EMA_2'] = np.mean(trader_state['PAIR1']['RAW_SIGNALS'])
    else:
        trader_state['PAIR1']['EMA_1'] = ema_calculate(raw_signal,trader_state['PAIR1']['EMA_1'], 1/win1)
        trader_state['PAIR1']['EMA_2'] = ema_calculate(raw_signal,trader_state['PAIR1']['EMA_2'], 1/win2)
    if len(trader_state['PAIR1']['RAW_SIGNALS']) < 10:
        return [], []
    if len(trader_state['PAIR1']['RAW_SIGNALS']) > 100:
        trader_state['PAIR1']['RAW_SIGNALS'].pop(0)
    
    signal_std = np.std(trader_state['PAIR1']['RAW_SIGNALS'])
    z_score = -1*(trader_state['PAIR1']['EMA_1']-trader_state['PAIR1']['EMA_2'])*20

    trader_state['PAIR1']['PAST_SIGNALS'].append(z_score)
    if len(trader_state['PAIR1']['PAST_SIGNALS']) > 20:
        trader_state['PAIR1']['PAST_SIGNALS'].pop(0)
    past_zscore = trader_state['PAIR1']['PAST_SIGNALS'][0]
    print(f"ZSCORE {z_score:.3} {trader_state['PAIR1']['EMA_1']:.3} {trader_state['PAIR1']['EMA_2']:.3} {signal_std:.3}", end='')
    
    curr_pos1 = state.position.get(sym1, 0)
    curr_pos2 = state.position.get(sym2, 0)
    # Target position based on pina coladas
    target_pos2, action = target_pairs_position(z_score, past_zscore, curr_pos2)
    # Clip
    target_pos2 = max(target_pos2, -POSITION_LIMITS[sym2])
    target_pos2 = min(target_pos2, POSITION_LIMITS[sym2])

    target_pos1 = target_pos2*-2

    if curr_pos1 == target_pos1 and curr_pos2 == target_pos2:
        return [], []
    orders1, orders2 = [], []

    if action == 'exit_passive' or action == 'exit_active':
        active_vol1, active_vol2 = 0, 0

        if action == 'exit_active':
            active_vol1 = abs(curr_pos1)
            active_vol2 = abs(curr_pos2)
        elif abs(curr_pos1)//2 > abs(curr_pos2):
            active_vol1 = abs(curr_pos1)-abs(curr_pos2)*2
        elif abs(curr_pos1)//2 < abs(curr_pos2):
            active_vol2 = abs(curr_pos2)-abs(curr_pos1)//2

        if curr_pos1 > 0:
            if active_vol1 > 0:
                active_vol1 = min(active_vol1, bid_sizes1[0])
                orders1.append(AlgoOrder(sym1, bids1[0], 'SELL', active_vol1, note=f'Pair_exit_active'))
            passive_vol1 = min(MAX_POST_SIZE[sym1], curr_pos1-active_vol1)
            if passive_vol1 > 0:
                orders1.append(AlgoOrder(sym1, bids1[0]+1, 'SELL', passive_vol1, note=f'Pair_exit_passive'))
        else:
            if active_vol1 > 0:
                active_vol1 = min(active_vol1, ask_sizes1[0])
                orders1.append(AlgoOrder(sym1, asks1[0], 'BUY', active_vol1, note=f'Pair_exit_active'))

            passive_vol1 = min(MAX_POST_SIZE[sym1], abs(curr_pos1)-active_vol1)
            if passive_vol1 > 0:
                orders1.append(AlgoOrder(sym1, asks1[0]-1, 'BUY', passive_vol1, note=f'Pair_exit_passive'))
        
        if curr_pos2 > 0:
            if active_vol2 > 0:
                active_vol2 = min(active_vol2, bid_sizes2[0])
                orders2.append(AlgoOrder(sym2, bids2[0], 'SELL', active_vol2, note=f'Pair_exit_active'))

            passive_vol2= min(MAX_POST_SIZE[sym2], curr_pos2-active_vol2)
            if passive_vol2 > 0:
                orders2.append(AlgoOrder(sym2, bids2[0]+1, 'SELL', passive_vol2, note=f'Pair_exit_passive'))
        else:
            if active_vol2 > 0:
                active_vol2 = min(active_vol2, ask_sizes2[0])
                orders2.append(AlgoOrder(sym2, asks2[0], 'BUY', active_vol2, note=f'Pair__exit_active'))

            passive_vol2 = min(MAX_POST_SIZE[sym2], abs(curr_pos2)-active_vol2)
            if passive_vol2 > 0:
                orders2.append(AlgoOrder(sym2, asks2[0]-1, 'BUY', passive_vol2, note=f'Pair_exit_passive'))

    elif action == 'enter_short':
        # SELL PINA COLADA, BUY COCONUT
        order_sz = curr_pos2 - target_pos2
        order_sz = min(order_sz, bid_sizes2[0], ask_sizes1[0]//2)

        # order_sz1 = min(order_sz1, ask_sizes1[sym1])
        orders1.append(AlgoOrder(sym1, asks1[0], 'BUY', order_sz*2, note=f'Pair_{action}'))

        # order_sz2 = min(order_sz2, bid_sizes2[sym2])
        orders2.append(AlgoOrder(sym2, bids2[0], 'SELL', order_sz, note=f'Pair_{action}'))

    elif action == 'enter_long':
        # BUY PINA COLADA, SELL COCONUT
        order_sz = target_pos2-curr_pos2
        order_sz = min(order_sz, bid_sizes1[0]//2, ask_sizes2[0])

        # order_sz1 = min(order_sz1, ask_sizes1[sym1])
        orders1.append(AlgoOrder(sym1, bids1[0], 'SELL', order_sz*2, note=f'Pair_{action}'))

        # order_sz2 = min(order_sz2, bid_sizes2[sym2])
        orders2.append(AlgoOrder(sym2, asks2[0], 'BUY', order_sz, note=f'Pair_{action}'))


    return orders1, orders2


class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        print(f"State: {state.timestamp}")

        for product in ['BANANAS','PEARLS']:
            if product in state.order_depths.keys():
                orders: list[Order] = alpha_trade(state, product)
                if orders:
                    result[product] = orders

        # for product in ['COCONUTS', 'PINA_COLADAS']:
        #     if product in state.order_depths.keys():
        #         orders: list[Order] = alpha_trade_pair1(state, product, PAIRS[product])
        #         if orders:
        #             result[product] = orders
        if 'COCONUTS' in state.order_depths.keys() and 'PINA_COLADAS' in state.order_depths.keys():
            orders1, orders2 = alpha_trade_pair1(state)
            if orders1:
                result['COCONUTS'] = orders1
            if orders2:
                result['PINA_COLADAS'] = orders2
        update_state_trades(state)
        print(f'\n{state.timestamp} {state.toJSON()}')
        if result:
            log_orders(state.timestamp, result)

        if result:
            for product in result.keys():
                orders = [o.create_market_order() for o in result[product]]
                result[product] = orders

        return result
