__author__ = 'saeedamen'

"""
A basic fixed beta trading strategy.
"""
from connection import Client

class PairsTrader(Client):

    def __init__(self, X:str, Y:str, thresholds:list, lookback_window:int,
                 zscoring_period:int, timeframe:str='day'):
        """
        Pairs trader initialization.
        """
        super().__init__()
        #check if the assets are active for trading
        self.X = X
        self.Y = Y
        self.long_entry = thresholds[0][0]
        self.long_exit = thresholds[0][1]
        self.short_entry = thresholds[1][0]
        self.short_exit = thresholds[1][1]
        self.window = lookback_window
        self.zscore_p = zscoring_period
        self.open_positions = False

    def get_data(self, asset:str):
        pass

    def check_entry_position(self, spread:pd.Series):
        pass

    def check_exit(self, spread:pd.Series):
        pass

    def OMS(self):
        pass

    def run(self):
        #get the historical data for X and Y pair
        #check if it holds the criteria.
        #get the spreads z-score
        #check if any entry position is triggered
        if self.open_positions:
            #check if any exit position is triggered only
            #in case of on going position
        pass
