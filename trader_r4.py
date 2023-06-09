from typing import Dict, List, Union
from datamodel import OrderDepth, TradingState, Order
import json
import math

import numpy as np

POSITION_LIMITS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "DIVING_GEAR": 50,
    "BERRIES": 250,
    "BAGUETTE": 150,
    "DIP": 300,
    "UKULELE": 70,
    "PICNIC_BASKET": 70,
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

"""
HISTORICAL DATA DICTIONARY
Parameters to store:
- Past dolphin sighting
- Dolphin sighting ema
- Diving gear price ema
- Basket signal ema
- Pair signal ema
"""
hist_data = {
    'last_time': 0
    # 'DOLPHINS': [],
    # 'BASKET_SIGNAL'
    # PAIR_SIGNAL
}

PAIR_SYMBOLS = ['PINA_COLADAS','COCONUTS']
PAIR_WEIGHTS = [-1, 15/8]

BASKET_COMPONENTS = ['PICNIC_BASKET','DIP','BAGUETTE','UKULELE']
BASKET_WEIGHTS = [-1, 4, 2, 1]

class AlgoOrder:
    def __init__(self, symbol: str, price: int, side: Union[int, str], quantity: int, note: str = 'None'):
        self.symbol = symbol
        self.price = price
        if side == 'BUY' or side == 1:
            self.side = 1
        elif side == 'SELL' or side == -1:
            self.side = -1
        self.quantity = int(quantity)
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
    
def offset_berries(fair_px: float, curr_pos: int, timestamp: int):

    if timestamp >= 3500 and timestamp <= 7500:
        return fair_px-0.005*curr_pos
    else:
        return fair_px-0.008*curr_pos

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

def ema_calculate(new_entry, prev_ema, alpha):
    return new_entry*alpha+prev_ema*(1-alpha)

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
    # fair_buy_px = fair_px - 0.25
    # fair_sell_px = fair_px + 0.25

    if product == 'BANANAS':
        passive_trades_bananas(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)
    elif product == 'PEARLS':
        passive_trades_pearls(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell)

    return orders

def get_pair_positions(px_signal, signal_ema, curr_pos):
    """
    Positive side means buy basket
    Positions will be returned as absolute values
    """
    side = np.sign(px_signal)
    abs_signal = abs(px_signal)
    target_pos = curr_pos.copy()
    # Maximum position at 3
    entry = 1.25
    exit = 0.25

    curr_rel_pos = [0,0]
    for i in range(2):
        # Get absolute relative positions
        curr_rel_pos[i] = -side*curr_pos[i]/PAIR_WEIGHTS[i]

    if abs_signal > entry or max(curr_rel_pos) > 0:
        # Enter whenever the signal falls lower than
        min_pos = max(curr_rel_pos)
        target_min = math.floor((abs_signal-entry)*150+5)
        if abs_signal > entry and side*(px_signal-signal_ema) < -0.1:
        # #     # Increase bet size if signal has began to trend down but still above entry
            target_min = max(min_pos + 100, target_min+100)

        target_min = min(target_min, POSITION_LIMITS['PINA_COLADAS'])
            # Adjust for previous high signals
        min_pos = max(min_pos,target_min)
        target_pos = [-side*round(min_pos*PAIR_WEIGHTS[i]) for i in range(2)]

    if curr_pos[0] > 0 or curr_pos[1] < 0:
        if px_signal < exit and px_signal-signal_ema >= 0:
            side = -np.sign(curr_pos[0])
            target_pos = [0,0]
        elif px_signal < (exit+0.25) and curr_pos[0] == 0 and curr_pos[1] < 0:
            side = -1
            target_pos = [0,0]
        # elif px_signal > exit and signal_ema < exit:
        #     side = -1
        #     target_pos = [0,0]

    elif curr_pos[0] < 0 or curr_pos[1] > 0:
        if px_signal > -exit and px_signal-signal_ema <= 0:
            side = -np.sign(curr_pos[0])
            target_pos = [0,0]
        elif px_signal > -(exit+0.25) and curr_pos[0] == 0 and curr_pos[1] > 0:
            side = 1
            target_pos = [0,0]
        # elif px_signal < -exit and signal_ema > -exit:
        #     side = 1
        #     target_pos = [0,0]

    for i in range(2):
        # Ensure that position is valid
        target_pos[i] = min(abs(target_pos[i]), POSITION_LIMITS[PAIR_SYMBOLS[i]])*np.sign(target_pos[i])

    return target_pos, side

def get_pair_sym_trade(sym, curr_pos, target_pos, side, bids, asks, bid_szs, ask_szs):
    """
    Taker trade
    """
    order_qty = (target_pos - curr_pos)*side
    if order_qty == 0:
        return None

    note = 'PAIR_TRADE'
    # Cross into first level
    if side == 1:
        # if asks[0] - bids[0] > 1:
        #     order_px = asks[0]-1
        #     note += "_PASSIVE"
        # else:
        order_px = asks[0]
    elif side == -1:
        # if asks[0] - bids[0] > 1:
        #     order_px = bids[0]+1
        #     note += "_PASSIVE"
        # else:
        order_px = bids[0]
    else:
        order_px = (bids[0]+asks[0])/2 # mid px default
        print("ERROR WITH ORDER PRICE")

    order_qty = min(order_qty, MAX_POST_SIZE[sym])

    return AlgoOrder(sym, order_px, side, order_qty, note=note)

def alpha_trade_pair(state: TradingState, result_orders: Dict[str, List[Order]]):

    # 0-PINA COLADAS, 1-COCONUTS
    bids, asks, bid_szs, ask_szs = [], [], [], []
    curr_pos = []
    for sym in PAIR_SYMBOLS:
        valid, bidi, aski, bid_szi, ask_szi = get_bids_asks(state.order_depths[sym])
        if not valid:
            return
        bids.append(bidi)
        asks.append(aski)
        bid_szs.append(bid_szi)
        ask_szs.append(ask_szi)
        curr_pos.append(state.position.get(sym, 0))
        
    mids = [0,0]
    for i in range(2):
        mids[i] = (bids[i][0] + asks[i][0])/2
    px_signal = -400*(mids[0]/mids[1]-15/8)

    global hist_data
    signal_ema2 = hist_data.get('PAIR_SIGNAL_EMA2', px_signal)
    hist_data['PAIR_SIGNAL_EMA2'] = ema_calculate(px_signal, signal_ema2, 1/50)

    target_pos, side = get_pair_positions(px_signal, signal_ema2,  curr_pos)
    
    for i, sym in enumerate(PAIR_SYMBOLS):
        trade = get_pair_sym_trade(sym, curr_pos[i], target_pos[i], -1*side*np.sign(PAIR_WEIGHTS[i]), bids[i], asks[i], bid_szs[i], ask_szs[i])
        if trade:
            result_orders[sym] = [trade]

    return

def alpha_trade_diving_gear(state: TradingState):
    order_depth: OrderDepth = state.order_depths['DIVING_GEAR']
    valid, bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth)
    if not valid:
        return []
    
    dolphins = state.observations.get('DOLPHIN_SIGHTINGS', None)
    if dolphins == None:
        return []
    curr_pos = state.position.get('DIVING_GEAR', 0)
    orders = []
    mid = (bids[0] + asks[0])/2
    
    global hist_data
    px_ema = hist_data.get('DG_PX_EMA', mid)
    prev_dolphins = hist_data.get('prev_dolphins', dolphins-1)
    dolphins_ema = hist_data.get('dolphins_ema', dolphins)

    dolphin_signal = dolphins - prev_dolphins
    target_pos = curr_pos
    # Desired position if trading
    if abs(dolphin_signal) > 5:
        side = np.sign(dolphin_signal)
        target_pos = POSITION_LIMITS['DIVING_GEAR']*side
        hist_data['trading_dolphins'] = side
    elif hist_data.get('trading_dolphins', 0) != 0:
        if (dolphins-dolphins_ema)*hist_data.get('trading_dolphins',0) <= 0:
            # dolphin momentum stopped
            hist_data['trading_dolphins'] = 0
        else:
            target_pos = POSITION_LIMITS['DIVING_GEAR']*hist_data.get('trading_dolphins',0)

    if curr_pos != 0:
        if hist_data.get('trading_dolphins', 0) == 0:
            # Exit after price and dolphin trend has stopped
            if curr_pos > 0 and mid <= px_ema:
                target_pos = 0
            elif curr_pos < 0 and mid >= px_ema:
                target_pos = 0
    
    # Create trade
    if target_pos != curr_pos:
        if target_pos > curr_pos:
            new_order = AlgoOrder('DIVING_GEAR', asks[0]+1,'BUY', target_pos-curr_pos,note=f"DG_ORDER_{hist_data.get('trading_dolphins', 0)}")
        else:
            new_order = AlgoOrder('DIVING_GEAR', bids[0]-1,'SELL', curr_pos-target_pos,note=f"DG_ORDER_{hist_data.get('trading_dolphins', 0)}")
        orders.append(new_order)
                
    hist_data['DG_PX_EMA'] = ema_calculate(mid, px_ema, 1/80)
    if dolphins != prev_dolphins:
        hist_data['prev_dolphins'] = dolphins
        hist_data['dolphins_ema'] = ema_calculate(dolphins, dolphins_ema, 1/20)

    return orders


def berries_time_offset(time):
    horizon = 100
    if time >= 3900 and time <= 4900:
        # Berries, ripening, expect price to drift in 20 steps
        return horizon*0.04
    elif time >= 5200 and time <= 6000:
        # Berries decayingy, expect price to drift in 20 steps
        return -horizon*0.04
    elif time >= 6000 and time <= 6500:
        # Berries decayingy, expect price to drift in 20 steps
        return -horizon*0.02
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

    if not (time >= 4800 and time <= 6500):
        if asks[0] < fair_buy_px and long_vol_avail:
            take_size = min(long_vol_avail, ask_sizes[0])
            long_vol_avail -= take_size
            ask_sizes[0] -= take_size
            curr_pos += take_size # Adjust position for posting
            active_buy = 1   
            orders.append(AlgoOrder(product, asks[0], 'BUY', take_size, note=f'X_0'))
    if not (time >= 4000 and time <= 4800):
        if bids[0] > fair_sell_px and short_vol_avail:
            take_size = min(short_vol_avail, bid_sizes[0])
            short_vol_avail -= take_size
            bid_sizes[0] -= take_size
            curr_pos -= take_size # Adjust position for posting
            active_sell = 1
            orders.append(AlgoOrder(product, bids[0], 'SELL', take_size, note=f'X_0'))

    fair_px = compute_fair_price(bids, bid_sizes, asks, ask_sizes)
    fair_px = offset_fair_price(product, fair_px, curr_pos, time)

    post_buy_levels = post_sell_levels = 3
    if px_time_offset > 0:
        fair_sell_px = fair_px + px_time_offset
        post_buy_levels = 3
        # Buy more aggressively

    if px_time_offset < 0:
        fair_buy_px = fair_px + px_time_offset
        post_sell_levels = 3
        # Sell more aggressively

    orders = passive_trades_general(state, product, orders, fair_buy_px, fair_sell_px, curr_pos, long_vol_avail, short_vol_avail, bids, asks, bid_sizes, ask_sizes, active_buy, active_sell, post_buy_levels, post_sell_levels)

    return orders


def get_basket_signal(mids):
    """
    # TODO: UPDATE TO USE BIDS/ASKS
    postive signal means that basket is underpriced compared to components
    """
    px_diff = -400
    for i in range(4):
        px_diff -= mids[i]*BASKET_WEIGHTS[i]
    # Convert to z-score and flip to indicate if basket is under or overpriced
    signal = -px_diff/100
    # print(f"SIGNAL: {signal}")

    return signal

def get_basket_positions(px_signal, signal_ema, curr_pos):
    """
    Positive side means buy basket
    Positions will be returned as absolute values
    """
    side = np.sign(px_signal)
    abs_signal = abs(px_signal)
    target_pos = curr_pos.copy()

    # Maximum position at 2
    entry = 1.25
    exit = 0.25

    curr_rel_pos = [0,0,0,0]
    for i in range(4):
        # Get absolute relative positions
        curr_rel_pos[i] = -side*curr_pos[i]/BASKET_WEIGHTS[i]

    if abs_signal > entry:
        # Enter whenever the signal falls lower than
        min_pos = max(curr_rel_pos)
        target_min = math.floor((abs_signal-entry)*35+5)
        if abs_signal > entry-0.25 and side*(px_signal-signal_ema) < -0.05:
            # Increase bet size if signal has began to trend down but still above entry
            target_min = max(min_pos+25, target_min+25)

        target_min = min(target_min, POSITION_LIMITS['PICNIC_BASKET'])
            # Adjust for previous high signals
        min_pos = max(min_pos,target_min)
        target_pos = [-side*round(min_pos*BASKET_WEIGHTS[i]) for i in range(4)]

    if curr_pos[0] > 0 or curr_pos[1] < 0 or curr_pos[2] < 0 or curr_pos[3] < 0:
        if px_signal < exit and px_signal-signal_ema >= 0:
            side = -1
            target_pos = [0,0,0,0]

    elif curr_pos[0] < 0 or curr_pos[1] > 0 or curr_pos[1] > 0 or curr_pos[3] > 0:
        if px_signal > -exit and px_signal-signal_ema <= 0:
            side = -np.sign(curr_pos[0])
            target_pos = [0,0,0,0]

    for i in range(4):
        # Ensure that position is valid
        target_pos[i] = min(abs(target_pos[i]), POSITION_LIMITS[BASKET_COMPONENTS[i]])*np.sign(target_pos[i])

    return target_pos, side


def get_basket_sym_trade(sym, curr_pos, target_pos, side, bids, asks, bid_szs, ask_szs):
    """
    Taker trade
    """
    order_qty = (target_pos - curr_pos)*side
    if order_qty == 0:
        return None

    level = 0 if sym == 'PICNIC_BASKET' else 0
    # Go aggressive into second level
    if side == 1:
        order_px = asks[0]+level
    elif side == -1:
        order_px = bids[0]-level
    else:
        order_px = (bids[0]+asks[0])/2 # mid px default
        print("ERROR WITH ORDER PRICE")

    return AlgoOrder(sym, order_px, side, order_qty, note='BASKET_TRADE')


def alpha_trade_basket(state: TradingState, result_orders: Dict[str, List[Order]]):

    # 0-BASKET, 1-DIP, 2-BAGUETTE, 3-UKULELE
    bids, asks, bid_szs, ask_szs = [], [], [], []
    curr_pos = []
    for sym in BASKET_COMPONENTS:
        valid, bidi, aski, bid_szi, ask_szi = get_bids_asks(state.order_depths[sym])
        if not valid:
            return
        bids.append(bidi)
        asks.append(aski)
        bid_szs.append(bid_szi)
        ask_szs.append(ask_szi)
        curr_pos.append(state.position.get(sym, 0))
        
    mids = [0,0,0,0]
    for i in range(4):
        mids[i] = (bids[i][0] + asks[i][0])/2

    px_signal = get_basket_signal(mids)
    global hist_data
    signal_ema = hist_data.get('BASKET_SIGNAL_EMA', px_signal)

    hist_data['BASKET_SIGNAL_EMA'] = ema_calculate(px_signal, signal_ema, 1/50)

    target_pos, side = get_basket_positions(px_signal, signal_ema,  curr_pos)
    
    for i, sym in enumerate(BASKET_COMPONENTS):
        trade = get_basket_sym_trade(sym, curr_pos[i], target_pos[i], -1*side*np.sign(BASKET_WEIGHTS[i]), bids[i], asks[i], bid_szs[i], ask_szs[i])
        if trade:
            result_orders[sym] = [trade]

    return


class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        global hist_data
        # For debugging loss of state
        print(f"T={hist_data.get('last_time',0)}")
        hist_data['last_time'] = state.timestamp

        for product in ['BANANAS','PEARLS']:
            if product in state.order_depths.keys():
                orders: list[Order] = alpha_trade(state, product)
                if orders:
                    result[product] = orders

        if 'PINA_COLADAS' in state.order_depths.keys():
            alpha_trade_pair(state, result)
        
        if 'DIVING_GEAR' in state.order_depths.keys():
            orders = alpha_trade_diving_gear(state)
            if orders:
                result['DIVING_GEAR'] = orders

        if 'BERRIES' in state.order_depths.keys():
            orders = alpha_trade_berries(state)
            if orders:
                result['BERRIES'] = orders
        
        if 'PICNIC_BASKET' in state.order_depths.keys():
            alpha_trade_basket(state, result)
        
        update_state_trades(state)
        print(f'\n{state.timestamp} {state.toJSON()}')
        if result:
            log_orders(state.timestamp, result)

        if result:
            for product in result.keys():
                orders = [o.create_market_order() for o in result[product]]
                result[product] = orders

        return result
