"""
Version 1: 
Hitting quotes that cross fair price
"""

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

    if len(order_depth.sell_orders) > 0:
        best_ask = min(order_depth.sell_orders.keys())
        best_ask_volume = order_depth.sell_orders[best_ask]

        if best_ask <= acceptable_price:
            orders.append(Order(product, best_ask, -best_ask_volume))

    if len(order_depth.buy_orders) != 0:
        best_bid = max(order_depth.buy_orders.keys())
        best_bid_volume = order_depth.buy_orders[best_bid]
        if best_bid >= acceptable_price:
            orders.append(Order(product, best_bid, -best_bid_volume))

    return orders

"""
Version 2
"""
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
    if best_ask <= acceptable_price:
        orders.append(Order(product, best_ask, max_long_order))
    else:
        # Make Market
        post_px = int(np.floor(acceptable_price))-1
        orders.append(Order(product, post_px, max_long_order))

    # Sell Order
    # Hit and leave remaining on the quote
    if best_bid >= acceptable_price:
        orders.append(Order(product, best_bid, max_short_order))
    else: 
        # Make Market
        post_px = int(np.ceil(acceptable_price))+1

        orders.append(Order(product, post_px, max_short_order))

    return orders

# Version 3

def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    acceptable_price = compute_fair_price(order_depth)
    curr_position = state.position.get(product, 0)

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_position
    short_vol_avail = -POSITION_LIMITS[product]-curr_position

    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
    else:
        return
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
    else:
        return 
    
    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0]:
            post_px -= 2
        elif post_px-1 > bids[0]:
            post_px -= 1

        post_sz = min(10, long_vol_avail)
        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 > asks[0]:
            post_px += 2
        elif post_px+1 > asks[0]:
            post_px += 1
        post_sz = max(-10, short_vol_avail)
        orders.append(Order(product, post_px, post_sz))

    return orders

# version 4
def alpha_trade(state: TradingState, product, orders: List[Order]):
    order_depth: OrderDepth = state.order_depths[product]
    acceptable_price = compute_fair_price(order_depth)
    curr_position = state.position.get(product, 0)

    # Adjust theo
    acceptable_price += curr_position*THEO_OFFSET_COEFF[product]

    # Positive and negative
    long_vol_avail = POSITION_LIMITS[product]-curr_position
    short_vol_avail = -POSITION_LIMITS[product]-curr_position

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
    
    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0] or (post_px-2 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 2
        elif post_px-1 > bids[0] or (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 1

        post_sz = min(10, long_vol_avail)
        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 > asks[0] or (post_px+2==asks[0] and ask_sizes[0] <= 2):
            post_px += 2
        elif post_px+1 > asks[0] or (post_px+1==asks[0] and ask_sizes[0] <=2):
            post_px += 1
        post_sz = max(-10, short_vol_avail)
        orders.append(Order(product, post_px, post_sz))

    return orders


# version 6

def alpha_trade(state: TradingState, product, orders: List[Order]):
    ...
    
    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0]:
            post_px -= 2
        elif post_px-1 > bids[0] or (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 1

        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 > asks[0]:
            post_px += 2
        elif post_px+1 > asks[0] or (post_px+1==asks[0] and ask_sizes[0] <=2):
            post_px += 1

        orders.append(Order(product, post_px, post_sz))

    return orders

# Version 7
def alpha_trade(state: TradingState, product, orders: List[Order]):
    ...
    
    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0] or (post_px-2 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 2
        elif post_px-1 > bids[0] or (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 1

        post_sz = long_vol_avail
        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 > asks[0] or (post_px+2==asks[0] and ask_sizes[0] <= 2):
            post_px += 2
        elif post_px+1 > asks[0] or (post_px+1==asks[0] and ask_sizes[0] <=2):
            post_px += 1
        # post_sz = max(-10, short_vol_avail)
        post_sz = short_vol_avail

    return orders


# Version 8
def alpha_trade(state: TradingState, product, orders: List[Order]):
    ...
    if long_vol_avail:
        post_px = int(np.floor(acceptable_price))
        # Buying
        if post_px-2 > bids[0]:
            post_px -= 2
        elif post_px-1 > bids[0] or (post_px-1 == bids[0] and bid_sizes[0] <= 2):
            post_px -= 1

        post_sz = long_vol_avail # hard to get filled so send max order
        orders.append(Order(product, post_px, post_sz))
    if short_vol_avail:
        # Sell Orders
        post_px = int(np.ceil(acceptable_price))
        if post_px+2 < asks[0]:
            post_px += 2
        elif post_px+1 < asks[0] or (post_px+1==asks[0] and ask_sizes[0] >= -2):
            post_px += 1

        post_sz = short_vol_avail # Hard to get filled so just yolo it

        orders.append(Order(product, post_px, post_sz))





