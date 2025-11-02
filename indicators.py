import numpy as np
import pandas as pd

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    tp = (high + low + close) / 3.0
    mf = tp * volume
    pmf = mf.where(tp > tp.shift(), 0.0)
    nmf = mf.where(tp < tp.shift(), 0.0)
    pmf_sum = pmf.rolling(period, min_periods=period).sum()
    nmf_sum = nmf.rolling(period, min_periods=period).sum()
    mr = pmf_sum / (nmf_sum.replace(0, np.nan))
    mfi = 100 - (100 / (1 + mr))
    return mfi.fillna(50)

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume).fillna(0).cumsum()

def zscore(series: pd.Series, window: int = 50) -> pd.Series:
    ma = series.rolling(window, min_periods=window).mean()
    sd = series.rolling(window, min_periods=window).std()
    return (series - ma) / (sd.replace(0, np.nan))

def sma(series: pd.Series, window: int = 20) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()
