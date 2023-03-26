from trader_r3 import Trader

from datamodel import *
from typing import Any
import pandas as pd
import numpy as np
import statistics
import copy
import uuid
import json

import sys
sys.stdout = open('./backtest_logs/backtest.log','wt')

# Timesteps used in training files
TIME_DELTA = 100
# Please put all! the price and log files into
# the same directory or adjust the code accordingly

def process_prices(df_prices, time_limit) -> dict[int, TradingState]:
    states = {}
    for _, row in df_prices.iterrows():
        time: int = int(row["timestamp"])
        if time > time_limit:
            break
        product: str = row["product"]
        if states.get(time) == None:
            position: Dict[Product, Position] = {}
            own_trades: Dict[Symbol, List[Trade]] = {}
            market_trades: Dict[Symbol, List[Trade]] = {}
            observations: Dict[Product, Observation] = {}
            listings = {}
            depths = {}
            states[time] = TradingState(time, listings, depths, own_trades, market_trades, position, observations)

        states[time].listings[product] = Listing(product, product, product)
        if np.isnan(row["bid_price_1"]):
            states[time].observations[product] = row["mid_price"]
            continue
        depth = OrderDepth()
        if row["bid_price_1"]> 0:
            depth.buy_orders[row["bid_price_1"]] = int(row["bid_volume_1"])
        if row["bid_price_2"]> 0:
            depth.buy_orders[row["bid_price_2"]] = int(row["bid_volume_2"])
        if row["bid_price_3"]> 0:
            depth.buy_orders[row["bid_price_3"]] = int(row["bid_volume_3"])
        if row["ask_price_1"]> 0:
            depth.sell_orders[row["ask_price_1"]] = int(row["ask_volume_1"])
        if row["ask_price_2"]> 0:
            depth.sell_orders[row["ask_price_2"]] = int(row["ask_volume_2"])
        if row["ask_price_3"]> 0:
            depth.sell_orders[row["ask_price_3"]] = int(row["ask_volume_3"])
        
        states[time].order_depths[product] = depth

        if product not in states[time].position:
            states[time].position[product] = 0
            states[time].own_trades[product] = []
            states[time].market_trades[product] = []
    return states

def process_trades(df_trades, states: dict[int, TradingState], time_limit):
    for _, trade in df_trades.iterrows():
        time: int = trade['timestamp']
        if time > time_limit:
            break
        symbol = trade['symbol']
        if symbol not in states[time].market_trades:
            states[time].market_trades[symbol] = []
        t = Trade(
                symbol, 
                trade['price'], 
                trade['quantity'], 
                '', #trade['buyer'], 
                '', #trade['seller'], 
                time)
        states[time].market_trades[symbol].append(t)
       
current_limits = {
    'PEARLS': 20,
    'BANANAS': 20,
    'COCONUTS': 600,
    'PINA_COLADAS': 300,
    'DIVING_GEAR': 50,
    'BERRIES': 250,
}

# Setting a high time_limit can be harder to visualize
def simulate_alternative(round: int, day: int, trader, time_limit=999900):
    prices_path = f"{TRAINING_DATA_PREFIX}/prices_round_{round}_day_{day}.csv"
    trades_path = f"{TRAINING_DATA_PREFIX}/trades_round_{round}_day_{day}_nn.csv"
    df_prices = pd.read_csv(prices_path, sep=';')
    df_trades = pd.read_csv(trades_path, sep=';')
    states = process_prices(df_prices, time_limit)
    process_trades(df_trades, states, time_limit)
    position = copy.copy(states[0].position)
    for time, state in states.items():
        position = copy.copy(state.position)
        orders = trader.run(copy.copy(state))
        trades = clear_order_book(orders, state.order_depths, time, state.market_trades)
        if len(trades) > 0:
            grouped_by_symbol = {}
            for trade in trades:
                if grouped_by_symbol.get(trade.symbol) == None:
                    grouped_by_symbol[trade.symbol] = []
                n_position = position[trade.symbol] + trade.quantity 
                if abs(n_position) > current_limits[trade.symbol]:
                    print("ILLEGAL TRADE, WOULD EXCEED POSITION LIMIT, KILLING ALL REMAINING ORDERS")
                    print(json.dumps(trades,default=lambda o: o.__dict__, sort_keys=True))
                #     break
                position[trade.symbol] = n_position
                trade.quantity = abs(trade.quantity)
                grouped_by_symbol[trade.symbol].append(trade)
            if states.get(time + TIME_DELTA) != None:
                states[time + TIME_DELTA].own_trades = grouped_by_symbol
        if states.get(time + TIME_DELTA) != None:
            states[time + TIME_DELTA].position = position
    # create_log_file(states, day, trader)

def cleanup_order_volumes(org_orders: List[Order]) -> List[Order]:
    buy_orders, sell_orders = [], []

    for i in range(len(org_orders)):
        order_1 = org_orders[i]
        final_order = copy.copy(order_1)
        for j in range(i+1, len(org_orders)):
            order_2 = org_orders[j]
            if order_1 == order_2:
               continue 
            if order_1.price == order_2.price and order_2.quantity != 0:
                final_order.quantity += order_2.quantity
                order_2.quantity = 0
        if final_order.quantity < 0:
            sell_orders.append(final_order)
        elif final_order.quantity > 0:
            buy_orders.append(final_order)
    buy_orders.sort(key=lambda x: x.price, reverse=True) # order by most aggressive
    sell_orders.sort(key=lambda x: x.price) # order by most aggressive
    return buy_orders, sell_orders

def get_bids_asks(order_depth):
    if len(order_depth.buy_orders) != 0:
        bids = sorted(order_depth.buy_orders.keys(), reverse=True)
        bid_sizes = [order_depth.buy_orders[bid] for bid in bids]
    else:
        return [], [], [], []
    if len(order_depth.sell_orders) > 0:
        asks = sorted(order_depth.sell_orders.keys())
        ask_sizes = [abs(order_depth.sell_orders[ask]) for ask in asks]
    else:
        return [], [], [], []
    return bids, asks, bid_sizes, ask_sizes

def clear_order_book(trader_orders: dict[str, List[Order]], order_depth: dict[str, OrderDepth], time: int, market_trades) -> list[Trade]:
    trades = []
    for symbol in trader_orders.keys():
        if order_depth.get(symbol) != None:
            bids, asks, bid_sizes, ask_sizes = get_bids_asks(order_depth[symbol])
            best_bid = bids[0]
            best_ask = asks[0]
            buy_orders, sell_orders = cleanup_order_volumes(trader_orders[symbol])
            for order in buy_orders:
                while order.quantity > 0 and len(asks) > 0 and order.price >= asks[0]:
                    trade_sz = min(ask_sizes[0], order.quantity)
                    trades.append(Trade(symbol, asks[0], trade_sz, "Submission", "", time))
                    order.quantity -= trade_sz
                    ask_sizes[0] -= trade_sz
                    if ask_sizes[0] == 0:
                        asks.pop(0)
                        ask_sizes.pop(0)

            for order in sell_orders:
                while order.quantity < 0 and len(bids) > 0 and order.price <= bids[0]:
                    trade_sz = min(bid_sizes[0], abs(order.quantity))
                    trades.append(Trade(symbol, bids[0], -trade_sz, "", "Submission", time))
                    order.quantity += trade_sz # position inc
                    bid_sizes[0] -= trade_sz
                    if bid_sizes[0] == 0:
                        bids.pop(0)
                        bid_sizes.pop(0)
            m_trades = market_trades[symbol]
            m_trades.sort(key=lambda x: x.price)

            new_bid = bids[0] if len(bids) > 0 else best_bid
            new_ask = asks[0] if len(asks) > 0 else best_ask
            for t in m_trades:
                # Try to match market trades with orders that are still in the book
                if (t.price - best_bid) < (best_ask - t.price):
                    # Trade closer to bid, assume person is trying to sell
                    for order in buy_orders:
                        if order.quantity == 0:
                            continue
                        if order.price <= best_bid:
                            # Don't have queue priority
                            break
                        if order.price >= t.price:
                            trade_sz = min(order.quantity, t.quantity)
                            order.quantity -= trade_sz
                            t.quantity -= trade_sz
                            trades.append(Trade(symbol, order.price, trade_sz, "Submission", "", time))
                        else:
                            break
                        if t.quantity <= 0:
                            break
                elif (t.price - best_bid) > (best_ask - t.price):
                    # Close to ask, assume buyer
                    for order in sell_orders:
                        if order.quantity == 0:
                            continue
                        if order.price >= best_ask:
                            # Don't have queue priority
                            break
                        if order.price <= t.price:
                            # order quantity is negative because of backtest setup
                            trade_sz = min(-order.quantity, t.quantity)
                            order.quantity += trade_sz
                            t.quantity -= trade_sz
                            # negative cuz sell
                            trades.append(Trade(symbol, order.price, -trade_sz, "", "Submission", time))
                        else:
                            # no more matches
                            break
                        if t.quantity <= 0:
                            break

    return trades
                            
csv_header = "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss"
log_header = ['Sandbox logs:\n']

class Logger:

    # Set this to true, if u want to create
    # local logs
    local: bool 
    # this is used as a buffer for logs
    # instead of stdout
    local_logs: dict[int, str] 

    def __init__(self, local=False) -> None:
        self.logs = ""
        self.local = local
        if local:
            self.local_logs = {}

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        output = json.dumps({
            "state": state,
            "orders": orders,
            "logs": self.logs,
        }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True)
        if self.local:
            self.local_logs[state.timestamp] = output
        else:
            print(output)
        self.logs = ""

def create_log_file(states: dict[int, TradingState], day, trader: Trader):
    file_name = uuid.uuid4()
    with open(f'./backtest_logs/errors.log', 'w', encoding="utf-8") as f:
        f.writelines(log_header)
        csv_rows = []
        f.write('\n\n')
        for time, state in states.items():
            if logger != None:
                if logger.__getattribute__('local_logs') != None:
                    if logger.local_logs.get(time) != None:
                        f.write(f'{time} {logger.local_logs[time]}\n')
                        continue
            if time != 0:
                f.write(f'{time}\n')

        f.write(f'\n\n')
        f.write('Submission logs:\n\n\n')
        f.write('Activities log:\n')
        f.write(csv_header)
        for time, state in states.items():
            for symbol in state.order_depths.keys():
                f.write(f'{day};{time};{symbol};')
                bids_length = len(state.order_depths[symbol].buy_orders)
                bids = list(state.order_depths[symbol].buy_orders.items())
                bids_prices = list(state.order_depths[symbol].buy_orders.keys())
                bids_prices.sort()
                asks_length = len(state.order_depths[symbol].sell_orders)
                asks_prices = list(state.order_depths[symbol].sell_orders.keys())
                asks_prices.sort()
                asks = list(state.order_depths[symbol].sell_orders.items())
                if bids_length >= 3:
                    f.write(f'{bids[0][0]};{bids[0][1]};{bids[1][0]};{bids[1][1]};{bids[2][0]};{bids[2][1]};')
                elif bids_length == 2:
                    f.write(f'{bids[0][0]};{bids[0][1]};{bids[1][0]};{bids[1][1]};;;')
                elif bids_length == 1:
                    f.write(f'{bids[0][0]};{bids[0][1]};;;;;')
                else:
                    f.write(f';;;;;;')
                if asks_length >= 3:
                    f.write(f'{asks[0][0]};{asks[0][1]};{asks[1][0]};{asks[1][1]};{asks[2][0]};{asks[2][1]};')
                elif asks_length == 2:
                    f.write(f'{asks[0][0]};{asks[0][1]};{asks[1][0]};{asks[1][1]};;;')
                elif asks_length == 1:
                    f.write(f'{asks[0][0]};{asks[0][1]};;;;;')
                else:
                    f.write(f';;;;;;')
                f.write(f'{statistics.median(asks_prices + bids_prices)};0.0\n')

round = 3
day = 1
TRAINING_DATA_PREFIX = f"./hist_data/island-data-bottle-round-{round}"

# Adjust accordingly the round and day to your needs
if __name__ == "__main__":
    logger = Logger(local=True)
    trader = Trader()
    simulate_alternative(round, day, trader, 999900)