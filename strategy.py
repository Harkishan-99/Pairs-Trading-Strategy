__author__ = 'harkishansinghbaniya'

"""
A basic fixed beta trading strategy.
"""
import os
import sys
import time
import json
import logging
import datetime
import pandas as pd

from utils import _partial_criteria, get_zscore
from connection import Client

logging.basicConfig(filename='error.log',
                    level=logging.WARNING,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# setup the connection with the API
client = Client()
conn = client.connect()
api = client.api()

class PairsTrader:

    def __init__(self, X:str, Y:str, thresholds:list, lookback_window:int,
                 base_amount:int, timeframe:str='1D'):
        """
        Pairs trader initialization.
        """
        #check if the assets are active for trading
        self.X = X
        self.Y = Y
        self.long_entry = thresholds[0][0]
        self.long_exit = thresholds[0][1]
        self.short_entry = thresholds[1][0]
        self.short_exit = thresholds[1][1]
        self.window = lookback_window
        self.base_qty = base_amount/2
        self.open_positions = False
        self.open_order = None
        self.timeframe = timeframe

    def order_log(self, data:dict)->None:
        with open('orders.json', 'w') as fp:
            json.dump(data, fp)

    def get_price_data(self, asset:str, limit:int)->pd.Series:
        res = api.get_barset(asset, self.timeframe, limit=limit)
        df = res.df[asset]
        return df['close']

    def OMS(self, asset:str, qty:float)->None:
        if qty != 0:
            if qty > 0:
                side = 'buy'
            else:
                side = 'sell'
            QTY = abs(qty)
            resp = api.submit_order(symbol=asset,
                                    qty=QTY,
                                    side=side)
            self.order_log(resp)
        else:
            try:
                #close the existing order
                resp = api.close_position(asset)
                self.order_log(resp)
            except Exception as e:
                logging.exception(e)

    def get_ltp(self, asset:str):
        return api.get_last_trade(asset).price

    def place_order(self, beta:float, type:str='exit'):
        if type == 'long':
            Y_qty = int(self.get_ltp(self.Y)/self.base_qty)
            X_qty = int(self.get_ltp(self.X)*beta/self.base_qty)
            self.OMS(self.Y, Y_qty)
            self.OMS(self.X, -1*X_qty)
        elif type == 'short':
            Y_qty = int(self.get_ltp(self.Y)/self.base_qty)
            X_qty = int(self.get_ltp(self.X)*beta/self.base_qty)
            self.OMS(self.Y, -1*Y_qty)
            self.OMS(self.X, X_qty)
        elif type == 'exit':
            self.OMS(self.Y, 0)
            self.OMS(self.X, 0)

    def run(self)->None:
        #get the historical data for X and Y pair
        X = self.get_price_data(self.X, self.window)
        Y = self.get_price_data(self.Y, self.window)
        #check if it holds the criteria.
        passed, spread, beta = _partial_criteria(X, Y)

        if passed:
            #get the spreads z-score
            zscore = get_zscore(spread)
            if not self.open_positions:
                #check if any entry position is triggered
                if zscore[-1] < self.long_entry:
                    #LONG the spread (BUY Y SELL X)
                    self.place_order(beta, type='long')
                    self.open_positions = 1

                elif zscore[-1] > self.short_entry:
                    #SELL the spread
                    self.place_order(beta, type='short')
                    self.open_positions = -1
                else:
                    print(f"{datetime.datetime.now()} No signal found !")

            else :
                #check if any exit position is triggered only
                #in case of on going position
                if (zscore[-1] < self.short_exit and self.open_positions < 0) or\
                   (zscore[-1] > self.long_exit and self.open_positions > 0):
                    #close the spread postion
                    self.place_order(beta, type='exit')
                    self.open_positions = False
        else:
            if self.open_positions:
                self.place_order(None, type='exit')
                self.open_positions = False
            print("The pair is no longer statisfying the criteria's")
            logging.info("The pair is no longer statisfying the criteria's")
            sys.exit()

def get_sleep_value(timeframe:str):
    value, base = timeframe[:-1], timeframe[-1]
    if base.upper() == 'D':
        #daily
        return value*86400
    elif base.upper() == 'H':
        #hourly
        return value*3600
    elif base.upper() == 'M':
        #hourly
        return value*60
    else:
        raise ValueError("Timeframe not supported")

if __name__ == "__main__":
    clock = api.get_clock()

    #check if market is open
    if clock.is_open:
        pass
    else:
        time_to_open = clock.next_open - clock.timestamp
        print(
            f"Market is closed now going to sleep for \
            {time_to_open.total_seconds()//60} minutes")
        time.sleep(time_to_open.total_seconds())

    #start a strategy instance
    X = 'AZO'
    Y = 'AAP'
    thresholds = [(-1.5, 0), (1.5, 0)]
    lookback_window = 252 #last 6 months
    base_amount = 1000 #$
    timeframe = '1D'

    trader = PairsTrader(X, Y, thresholds, lookback_window,
                         base_amount, timeframe)
    bar_time = get_sleep_value(timeframe)
    while True:
        trader.run()
        print("No signal goin to sleep")
        #sleep till next bar
        time.sleep(bar_time)
