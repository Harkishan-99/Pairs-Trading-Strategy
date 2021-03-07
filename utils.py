import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller

def get_zscore(series, mean=None, std=None):
    """
    Returns the nromalized time series assuming a normal distribution
    """
    if mean is None:
        if std is None:
            return (series - series.mean()) / np.std(series)
    return (series - mean) / std


def check_for_stationarity(X, subsample=0):
    """
    H_0 in adfuller is unit root exists (non-stationary).
    We must observe significant p-value to convince ourselves that the series is stationary.

    :param X: time series
    :param subsample: boolean indicating whether to subsample series
    :return: adf results
    """
    if subsample != 0:
        frequency = round(len(X) / subsample)
        subsampled_X = X[0::frequency]
        result = adfuller(subsampled_X)
    else:
        result = adfuller(X)
    return {'t_statistic':result[0],
     'p_value':result[1],  'critical_values':result[4]}

def hurst(ts):
    """
    Returns the Hurst Exponent of the time series vector ts.
    Series vector ts should be a price series.
    Source: https://www.quantstart.com/articles/Basics-of-Statistical-Mean-Reversion-Testing"""
    lags = range(2, 100)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def check_coint(X, Y):
    """
    Engle-Granger test for cointegration.
    """
    result = coint(Y, X)
    return {'t_statistic':result[0],  'p_value':result[1],  'critical_values':result[2]}

def find_hurst_exp(ts: np.array) -> float:
    """Returns the Hurst Exponent of the time series vector ts"""
    lags = range(2, 100)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def find_half_life(ts: np.array) -> float:
    """ Find the half-life of mean-reversion of a timeseries """
    z_lag = np.roll(ts, 1)
    z_lag[0] = 0
    z_ret = ts - z_lag
    z_ret[0] = 0
    z_lag2 = sm.add_constant(z_lag)
    model = sm.OLS(z_ret, z_lag2)
    res = model.fit()
    halflife = -np.log(2) / res.params[1]
    return halflife

def find_mean_cross(ts: pd.Series) -> int:
    c1 = ts.loc[((ts.shift(1) < 0) & (ts > 0))]
    c2 = ts.loc[((ts.shift(1) > 0) & (ts < 0))]
    c = len(c1) + len(c2)
    return c

def _apply_full_criteria(X, Y, p_value_threshold=0.05, min_half_life=1, max_half_life=255, min_mean_cross=12, mean_cross_freq='1Y'):
    stats_X = check_for_stationarity(X.values)
    stats_Y = check_for_stationarity(Y.values)
    criteria_name = 'individual stationarity'
    if stats_X['p_value'] > p_value_threshold:
        if stats_Y['p_value'] > p_value_threshold:
            x = X.values
            y = Y.values
            x_ = sm.add_constant(x)
            results = sm.OLS(y, x_).fit()
            b = results.params[1]
            if b > 0:
                spread = Y - b * X
                stats = check_coint(X, Y)
                criteria_name = 'pair stationarity'
                if stats['p_value'] <= p_value_threshold:
                    criteria_name = 'hurst exponent'
                    hurst_exponent = find_hurst_exp(spread.values)
                    if hurst_exponent < 0.5:
                        criteria_name = 'half life'
                        hl = find_half_life(spread.values)
                        if hl <= max_half_life and hl >= min_half_life:
                            criteria_name = 'mean cross'
                            mean_cross = find_mean_crossover(spread, mean_cross_freq)
                            if mean_cross.mean() >= min_mean_cross:
                                result = {'coint_coef':b, 'spread':spread}
                                return (result, criteria_name)
    return (None, criteria_name)

def _partial_criteria(X, Y, p_value_threshold=0.05):
    stats_X = check_for_stationarity(X.values)
    stats_Y = check_for_stationarity(Y.values)
    if stats_X['p_value'] > p_value_threshold and \
        stats_Y['p_value'] > p_value_threshold:
        x = X.values
        y = Y.values
        x_ = sm.add_constant(x)
        results = sm.OLS(y, x_).fit()
        b = results.params[1]
        if b > 0:
            spread = Y - b * X
            stats = check_coint(X, Y)
            if stats['p_value'] <= p_value_threshold:
                hurst_exponent = find_hurst_exp(spread.values)
                if hurst_exponent < 0.5:
                    return True, spread, b
    return False, None, None
