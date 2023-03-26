from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import json

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "DIVING_GEAR": 50,
    "BERRIES": 250,
}

MAX_POST_SIZE = {
    "BANANAS": 20,
    "PEARLS": 12,
    "COCONUTS": 39,
    "PINA_COLADAS": 19,
    "BERRIES": 20,
}

PAIRS = {
    'COCONUTS': 'PINA_COLADAS',
    'PINA_COLADAS': 'COCONUTS'
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
    
def offset_berries(fair_px: float, curr_pos: int, timestamp: int):
    if timestamp >= 3500 and timestamp <= 7500:
        return fair_px-0.005*curr_pos
    else:
        return fair_px-0.0075*curr_pos

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
    "BERRIES": offset_berries,
    # "DIVING_GEAR": 
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


def passive_trades_general(state: TradingState, product, orders: List[Order], fair_buy_px, fair_sell_px, curr_pos: int, long_vol_avail: int, short_vol_avail: int, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell, post_buy_levels, post_sell_levels):
    # Adjust top of quote if we take it out
    best_bid = bids[active_sell] if len(bids) > active_sell else bids[0]-1
    best_bid_vol = bid_sizes[active_sell] if len(bids) > active_sell else long_vol_avail

    best_ask = asks[active_buy] if len(asks) > active_buy else asks[0]+1
    best_ask_vol = ask_sizes[active_buy] if len(asks) > active_buy else short_vol_avail

    max_post_sz = MAX_POST_SIZE[product]
    if long_vol_avail > 0:
        post_px = int(np.floor(fair_buy_px))
        posted = False
        for dx in range(post_buy_levels, 0, -1):
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
        for dx in range(post_sell_levels, 0, -1):
            if post_px + dx < best_ask:
                post_sz = min(short_vol_avail, max_post_sz)
                short_vol_avail -= post_sz
                orders.append(AlgoOrder(product, post_px+dx, 'SELL', post_sz, note=f'P{dx}'))
                posted = True
                break
        if not posted:
            post_sz = min(short_vol_avail, max_post_sz)
            orders.append(AlgoOrder(product, post_px, 'SELL', post_sz, note=f'P0'))

    return orders

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

def target_pairs_position(z_score, curr_pos1, curr_pos2):
    # Target position for pina coladas
    entry = 1
    pos_multiplier = 125
    if z_score >= entry:
        target_pos = np.floor((z_score-entry)*pos_multiplier)
        return target_pos, 'enter_long'
    if z_score <= -entry:
        target_pos = np.ceil((z_score+entry)*pos_multiplier)
        return target_pos, 'enter_short'

    exit_active = -0.5 # other side
    exit_slow = 0.25
    if curr_pos2 > 0 or curr_pos1 < 0:
        if z_score < exit_active:
            return 0, 'exit_active'
        elif z_score < exit_slow:
            return 0, 'exit_passive'
    
    if curr_pos2 < 0 or curr_pos1 > 0:
        if z_score > -exit_active:
            return 0, 'exit_active'
        elif z_score > -exit_slow:
            return 0, 'exit_passive'
    
    return curr_pos2, 'NO_TRADE'

def limit_take_qty(qty, side, bid_sizes, ask_sizes):
    if side == 1:
        return min(qty, ask_sizes[0])
    else:
        return min(qty, bid_sizes[0])
    
def get_passive_order(sym, side, qty, bids, asks, note=None, level=1):
    # Post on top of the current order book
    if side == 1:
        return AlgoOrder(sym, bids[0]+level, 'BUY', qty, note+'_P')
    else:
        return AlgoOrder(sym, asks[0]-level, 'SELL', qty, note+'_P')

def get_active_order(sym, side, qty, bids, asks, note=None):
    # Take top level of other side
    if side == 1:
        return AlgoOrder(sym, asks[0], 'BUY', qty, note+'_X')
    else:
        return AlgoOrder(sym, bids[0], 'SELL', qty, note+'_X')


def alpha_trade_pair1(state: TradingState):
    # Active only strategy for now
    sym1, sym2 = 'COCONUTS', 'PINA_COLADAS'
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
    signal = (mid2-15000)-2*(mid1-8000)
    signal /= -30
    
    curr_pos1 = state.position.get(sym1, 0)
    curr_pos2 = state.position.get(sym2, 0)
    # Target position based on pina coladas
    target_pos2, action = target_pairs_position(signal, curr_pos1, curr_pos2)
    # Clip
    target_pos2 = max(target_pos2, -POSITION_LIMITS[sym2])
    target_pos2 = min(target_pos2, POSITION_LIMITS[sym2])

    target_pos1 = target_pos2*-2
    if curr_pos1 == target_pos1 and curr_pos2 == target_pos2:
        return [], []
    orders1, orders2 = [], []

    side1, side2 = 0, 0
    active_vol1, active_vol2 = 0, 0
    passive_vol1, passive_vol2 = 0, 0

    if action == 'exit_active':
        active_vol1 = abs(curr_pos1)
        side1 = -np.sign(curr_pos1)
        active_vol1 = limit_take_qty(active_vol1, side1, bid_sizes1, ask_sizes1)

        side2 = -np.sign(curr_pos2)
        active_vol2 = limit_take_qty(active_vol2, side2, bid_sizes2, ask_sizes2)
    elif action == 'exit_passive':
        side1 = -np.sign(curr_pos1)
        side2 = -np.sign(curr_pos2)

        # Quantity for active hedge
        if abs(curr_pos1) > abs(curr_pos2)*2:
            active_vol1 = abs(curr_pos1)-abs(curr_pos2)*2
            active_vol1 = limit_take_qty(active_vol1, side1, bid_sizes1, ask_sizes1)
        elif abs(curr_pos1) < abs(curr_pos2)*2:
            active_vol2 = abs(curr_pos2)-abs(curr_pos1)//2
            active_vol2 = limit_take_qty(active_vol2, side2, bid_sizes2, ask_sizes2)

        passive_vol1 = min(MAX_POST_SIZE[sym1], abs(curr_pos1)-active_vol1)
        passive_vol2= min(MAX_POST_SIZE[sym2], abs(curr_pos2)-active_vol2)
    elif action == 'enter_short':
        side1, side2 = 1, -1
        # SELL PINA COLADA, BUY COCONUT
        passive_vol1 = target_pos1 - curr_pos1
        passive_vol2 = curr_pos2 - target_pos2

        # Active volume to ensure hedged
        # If position delta is relatively greater, trade some actively
        if passive_vol1 > passive_vol2*2:
            active_vol1 = passive_vol2*2-passive_vol1
            passive_vol1 -= active_vol1
        elif passive_vol1 < passive_vol2*2:
            active_vol2 = (passive_vol1-passive_vol2*2)//2
            passive_vol2 -= active_vol2

    elif action == 'enter_long':
        # BUY PINA COLADA, SELL COCONUT
        side1, side2 = -1, 1
        passive_vol1 = curr_pos1 - target_pos1 
        passive_vol2 = target_pos2 - curr_pos2

        # Active volume to ensure hedged
        # If position delta is relatively greater, trade some actively
        if passive_vol1 > passive_vol2*2:
            active_vol1 = passive_vol2*2-passive_vol1
            passive_vol1 -= active_vol1
        elif passive_vol1 < passive_vol2*2:
            active_vol2 = (passive_vol1-passive_vol2*2)//2
            passive_vol2 -= active_vol2

    passive_vol1 = min(passive_vol1, MAX_POST_SIZE[sym1])
    passive_vol2 = min(passive_vol2, MAX_POST_SIZE[sym2])
        
    if passive_vol1 > 0:
        orders1.append(get_passive_order(sym1, side1, passive_vol1, bids1, asks1, action))
    if passive_vol2 > 0:
        orders2.append(get_passive_order(sym2, side2, passive_vol2, bids2, asks2, action))
    if active_vol1 > 0:
        orders1.append(get_active_order(sym1, side1, active_vol1, bids1, asks1, action))
    if active_vol2 > 0:
        orders2.append(get_active_order(sym2, side2, active_vol2, bids2, asks2, action))

    return orders1, orders2

past_observations = {
    'DOLPHIN_SIGHTINGS': [],
}

# def alpha_trade_diving_gear(state: TradingState):
#     order_depth: OrderDepth = state.order_depths['DIVING_GEAR']
#     valid, bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth)
#     if not valid:
#         return []
    
#     dolphins = state.observations.get('DOLPHIN_SIGHTINGS', None)
#     if dolphins == None:
#         return []
    
#     global past_observations
#     past_dolphins = past_observations['DOLPHIN_SIGHTINGS']
#     past_observations['DOLPHIN_SIGHTINGS'] = dolphins

#     if past_dolphins == None:
#         return []

#     mid = (bids[0]+asks[0])/2
#     # fair_price = mid*0.999152+dolphins*0.0275947
#     signal = dolphins-past_dolphins

#     curr_pos = state.position.get('DIVING_GEAR', 0)

#     orders = []
#     if signal > 0 and curr_pos+signal < POSITION_LIMITS['DIVING_GEAR']:
#         size = 1
#         orders.append(AlgoOrder('DIVING_GEAR', asks[0], 'BUY', size, note=f'X0_DG'))
#     if signal < 0 and curr_pos+signal > -POSITION_LIMITS['DIVING_GEAR']:
#         size = 1

#         orders.append(AlgoOrder('DIVING_GEAR', bids[0], 'SELL', size, note=f'X0_DG'))

#     return orders

ichimoku_cloud_lines = {
    'past_dolphins': [],
}

def alpha_trade_diving_gear(state: TradingState):
    order_depth: OrderDepth = state.order_depths['DIVING_GEAR']
    valid, bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth)
    if not valid:
        return []
    
    dolphins = state.observations.get('DOLPHIN_SIGHTINGS', None)
    if dolphins == None:
        return []
    global past_observations
    past_dolphins = past_observations['DOLPHIN_SIGHTINGS']
    past_dolphins.append(dolphins)

    win1 = 25
    win2 = 75
    win3 = 200

    if len(past_dolphins) > win3:
        past_dolphins.pop(0)
    
    ichi_conversion = (max(past_dolphins[-win1:])+min(past_dolphins[-win1:]))/2
    ichi_base = (max(past_dolphins[-win2:])+min(past_dolphins[-win2:]))/2
    ichi_spanA = (ichi_base+ichi_conversion)/2
    ichi_spanB = (max(past_dolphins)+min(past_dolphins))/2

    lead = ichi_conversion-ichi_base
    cloud = ichi_spanA-ichi_spanB
    
    curr_pos = state.position.get('DIVING_GEAR', 0)
    orders = []

    if lead > 2 and cloud >= 0:
        # Enter
        target_pos = np.ceil(lead*5)
        size = min(target_pos-curr_pos, ask_sizes[0], POSITION_LIMITS['DIVING_GEAR']-curr_pos)
        if size > 0:
            orders.append(AlgoOrder('DIVING_GEAR', asks[0], 'BUY', size, note=f'X0_DG_ENTER'))

    elif lead < -2 and cloud <= 0:
        target_pos = np.ceil(lead*-5)
        size = min(target_pos-curr_pos, bid_sizes[0], curr_pos+POSITION_LIMITS['DIVING_GEAR'])
        if size > 0:
            orders.append(AlgoOrder('DIVING_GEAR', bids[0], 'SELL', size, note=f'X0_DG_ENTER'))

    elif curr_pos > 0 and cloud <= 0:
        # Close
        size = curr_pos
        orders.append(AlgoOrder('DIVING_GEAR', bids[0], 'SELL', size, note=f'X0_DG_EXIT'))
    elif curr_pos < 0 and cloud >= 0:
        size = abs(curr_pos)
        orders.append(AlgoOrder('DIVING_GEAR', asks[0], 'BUY', size, note=f'X0_DG_EXIT'))

    return orders


def berries_time_offset(time):
    horizon = 40
    if time >= 4050 and time <= 4950:
        # Berries, ripening, expect price to drift in 20 steps
        return horizon*0.0375
    elif time >= 5050 and time <= 6000:
        # Berries decayingy, expect price to drift in 20 steps
        return -horizon*0.035
    elif time >= 6000 and time <= 7000:
        # Berries decayingy, expect price to drift in 20 steps
        return -horizon*0.03
    elif time <= 3950 and time >= 3600:
        # Willing to accumulate a short position before berries start to grow
        return -horizon*0.025
    return 0


def alpha_trade_berries(state: TradingState):
    product = 'BERRIES'
    order_depth: OrderDepth = state.order_depths[product]
    valid, bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth)
    if not valid:
        return []
    orders = []
    time = state.timestamp / 100

    curr_pos = state.position.get(product, 0)
    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(product, fair_px, curr_pos, time)

    #TODO: Adjust fair price by time of day
    px_time_offset = berries_time_offset(time)
    fair_px += px_time_offset

    fair_buy_px = fair_sell_px = fair_px
    active_sell = active_buy = False
    long_vol_avail = POSITION_LIMITS[product]-curr_pos
    short_vol_avail = abs(-POSITION_LIMITS[product]-curr_pos)

    if not (time >= 4750 and time <= 7000):
        if asks[0] < fair_buy_px and long_vol_avail:
            take_size = min(long_vol_avail, ask_sizes[0])
            long_vol_avail -= take_size
            ask_sizes[0] -= take_size
            curr_pos += take_size # Adjust position for posting
            active_buy = 1   
            orders.append(AlgoOrder(product, asks[0], 'BUY', take_size, note=f'X_0'))
    if not (time >= 4250 and time <= 5250):
        if bids[0] > fair_sell_px and short_vol_avail:
            take_size = min(short_vol_avail, bid_sizes[0])
            short_vol_avail -= take_size
            bid_sizes[0] -= take_size
            curr_pos -= take_size # Adjust position for posting
            active_sell = 1
            orders.append(AlgoOrder(product, bids[0], 'SELL', take_size, note=f'X_0'))

    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(product, fair_px, curr_pos, time)
    fair_px += px_time_offset

    post_buy_levels = 3
    post_sell_levels = 3

    # if time >= 4050 and time <= 4950:
    #     post_buy_levels = 3
    # elif time >= 5050 and time <= 6950:
    #     post_sell_levels = 3

    orders = passive_trades_general(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell, post_buy_levels, post_sell_levels)

    return orders


class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        print(f"State: {state.timestamp}")

        for product in ['BANANAS','PEARLS']:
            if product in state.order_depths.keys():
                orders: list[Order] = alpha_trade(state, product)
                if orders:
                    result[product] = orders

        # if 'COCONUTS' in state.order_depths.keys() and 'PINA_COLADAS' in state.order_depths.keys():
        #     orders1, orders2 = alpha_trade_pair1(state)
        #     if orders1:
        #         result['COCONUTS'] = orders1
        #     if orders2:
        #         result['PINA_COLADAS'] = orders2
        
        # if 'DIVING_GEAR' in state.order_depths.keys():
        #     orders = alpha_trade_diving_gear(state)
        #     if orders:
        #         result['DIVING_GEAR'] = orders

        # if 'BERRIES' in state.order_depths.keys():
        #     orders = alpha_trade_berries(state)
        #     if orders:
        #         result['BERRIES'] = orders
        
        update_state_trades(state)
        print(f'\n{state.timestamp} {state.toJSON()}')
        if result:
            log_orders(state.timestamp, result)

        if result:
            for product in result.keys():
                orders = [o.create_market_order() for o in result[product]]
                result[product] = orders

        return result
