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
