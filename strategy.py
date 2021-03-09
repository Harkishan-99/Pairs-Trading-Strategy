__author__ = 'saeedamen'

"""
A basic fixed beta trading strategy.
"""
import os
import json
import logging
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
                 base_qty:int, timeframe:str='1D'):
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
        self.base_qty = base_qty
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

    def check_criteria(self, X:pd.Series, Y:pd.Series)->(bool, pd.Series, float):
        return _partial_criteria(X, Y)

    def OMS(self, asset:str, qty:float)->None:
        if qty != 0:
            if qty > 0:
                side = 'buy'
            else:
                side = 'sell'

            resp = api.submit_order(symbol=asset,
                                    qty=abs(qty),
                                    side=side)
            self.order_log(resp)
        else:
            try:
                #close the existing order
                resp = api.close_position(asset)
                self.order_log(resp)
            except Exception as e:
                logging.exception(e)

    def run(self)->None:
        #get the historical data for X and Y pair
        X = self.get_price_data(self.X, self.window)
        Y = self.get_price_data(self.Y, self.window)
        #check if it holds the criteria.
        passed, spread, beta = check_criteria(X, Y)
        #get the spreads z-score
        zscore = get_zscore(spread)
        if passed:
            #check if any entry position is triggered
            if zscore[-1] < self.long_entry:
                #BUY the spread (BUY Y SELL X)
                self.OMS(self.Y, 1)
                self.OMS(self.X, -1*beta)
                self.open_positions = 1
            elif zscore[-1] > self.short_entry:
                #SELL the spread
                #BUY the spread (BUY Y SELL X)
                self.OMS(self.Y, -1)
                self.OMS(self.X, 1*beta)
                self.open_positions = -1

            if self.open_positions:
                #check if any exit position is triggered only
                #in case of on going position
                if (zscore[-1] < self.short_exit and self.open_positions < 0) or\
                   (zscore[-1] > self.long_exit and self.open_positions > 0):
                    #close the spread postion
                    self.OMS(self.Y, 0)
                    self.OMS(self.X, 0)
                    self.open_positions = False
        else:
            if self.open_positions:
                self.OMS(self.Y, 0)
                self.OMS(self.X, 0)
                self.open_positions = False
