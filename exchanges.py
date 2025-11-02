import ccxt
import pandas as pd
import requests

BINANCE_FAPI = "https://fapi.binance.com"

def _ensure_exchange(name: str):
    cls = getattr(ccxt, name)
    return cls({'enableRateLimit': True})

def fetch_ohlcv(exchange_name: str, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    ex = _ensure_exchange(exchange_name)
    ex.load_markets()
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df

def fetch_ticker(exchange_name: str, symbol: str) -> dict:
    ex = _ensure_exchange(exchange_name)
    ex.load_markets()
    return ex.fetch_ticker(symbol)

def binance_funding_rate(symbol_usdm: str):
    url = f"{BINANCE_FAPI}/fapi/v1/premiumIndex"
    r = requests.get(url, params={"symbol": symbol_usdm}, timeout=10)
    r.raise_for_status()
    return r.json()

def binance_open_interest(symbol_usdm: str):
    url = f"{BINANCE_FAPI}/fapi/v1/openInterest"
    r = requests.get(url, params={"symbol": symbol_usdm}, timeout=10)
    r.raise_for_status()
    return r.json()

def market_pair_to_usdm(symbol_ccxt: str) -> str:
    return symbol_ccxt.replace("/", "")
