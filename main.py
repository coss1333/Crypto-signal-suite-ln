import os, time, argparse, math
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import requests

from exchanges import fetch_ohlcv, fetch_ticker, binance_funding_rate, binance_open_interest, market_pair_to_usdm
from indicators import rsi, mfi, obv, zscore, sma
from signal_engine import combine_rules

def send_telegram(msg: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print("Telegram error:", e)
        return False

def analyze_once(symbol: str, timeframe: str, lookback: int) -> dict:
    spot_ex = os.getenv("EXCHANGE_SPOT", "binance")
    fut_ex  = os.getenv("EXCHANGE_FUTURES", "binanceusdm")

    spot = fetch_ohlcv(spot_ex, symbol, timeframe, limit=lookback)
    fut  = fetch_ohlcv(fut_ex,  symbol, timeframe, limit=lookback)

    df = spot.copy()
    df["rsi"] = rsi(df["close"])
    df["mfi"] = mfi(df["high"], df["low"], df["close"], df["volume"])
    df["obv"] = obv(df["close"], df["volume"])
    df["obv_slope"] = df["obv"].diff().rolling(5, min_periods=1).mean()

    vol_ma = sma(df["volume"], 50)
    mult = float(os.getenv("VOLUME_SPIKE_MULTIPLIER","2.0"))
    df["vol_spike"] = df["volume"] > (vol_ma * mult)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    min_len = min(len(fut), len(spot))
    f_end = fut.tail(min_len).reset_index(drop=True)
    s_end = spot.tail(min_len).reset_index(drop=True)
    basis_series = f_end["close"] - s_end["close"]
    basis_z = zscore(basis_series, window=min(50, len(basis_series))).iloc[-1]
    basis_now = basis_series.iloc[-1]

    usdm_sym = market_pair_to_usdm(symbol)
    fr = binance_funding_rate(usdm_sym)
    funding = float(fr.get("lastFundingRate", 0.0))

    oi_raw = binance_open_interest(usdm_sym)
    oi = float(oi_raw.get("openInterest", 0.0))
    oi_change = 0.0

    ctx = {
        "spot_last": float(last["close"]),
        "spot_prev": float(prev["close"]),
        "fut_last": float(f_end.iloc[-1]["close"]),
        "rsi": float(last["rsi"]),
        "mfi": float(last["mfi"]),
        "obv_slope": float(last["obv_slope"]),
        "vol_spike": bool(last["vol_spike"]),
        "basis": float(basis_now),
        "basis_z": float(basis_z if not math.isnan(basis_z) else 0.0),
        "funding": funding,
        "oi": oi,
        "oi_change": oi_change,
        "rsi_ob": float(os.getenv("RSI_OVERBOUGHT", "70")),
        "rsi_os": float(os.getenv("RSI_OVERSOLD", "30")),
        "mfi_ob": float(os.getenv("MFI_OVERBOUGHT", "80")),
        "mfi_os": float(os.getenv("MFI_OVERSOLD", "20")),
        "basis_enter": float(os.getenv("BASIS_ZSCORE_ENTER", "1.5")),
        "basis_exit": float(os.getenv("BASIS_ZSCORE_EXIT", "0.5")),
    }

    sig = combine_rules(ctx)

    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "spot_last": ctx["spot_last"],
        "fut_last": ctx["fut_last"],
        "rsi": ctx["rsi"],
        "mfi": ctx["mfi"],
        "funding": ctx["funding"],
        "oi": ctx["oi"],
        "basis": ctx["basis"],
        "basis_z": ctx["basis_z"],
        "vol_spike": ctx["vol_spike"],
        "signal": sig.action,
        "score": sig.score,
        "reasons": sig.reasons,
        "timestamp": str(spot.iloc[-1]["timestamp"]),
    }
    return result

def format_report(res: dict) -> str:
    lines = [
        f"🔎 <b>{res['symbol']}</b>  tf {res['timeframe']}  @ {res['timestamp']}",
        f"Spot: {res['spot_last']:.4f} | Fut: {res['fut_last']:.4f} | Basis: {res['basis']:.4f} (z={res['basis_z']:.2f})",
        f"RSI: {res['rsi']:.1f} | MFI: {res['mfi']:.1f} | Funding: {res['funding']:.5f} | OI: {res['oi']:.0f}",
        f"Vol spike: {'Yes' if res['vol_spike'] else 'No'}",
        f"➡️ <b>Signal: {res['signal']}</b> (score {res['score']:+.2f})",
        ("• " + "\n• ".join(res["reasons"])) if res["reasons"] else "• No strong factors",
    ]
    return "\n".join(lines)

def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default=os.getenv("SYMBOL","BTC/USDT"))
    ap.add_argument("--timeframe", default=os.getenv("TIMEFRAME","5m"))
    ap.add_argument("--lookback", type=int, default=int(os.getenv("LOOKBACK","500")))
    ap.add_argument("--loop", action="store_true", help="Run continuously")
    ap.add_argument("--interval", type=int, default=60, help="Seconds between loops")
    args = ap.parse_args()

    while True:
        try:
            res = analyze_once(args.symbol, args.timeframe, args.lookback)
            report = format_report(res)
            print(report)

            sent = send_telegram(report)
            if sent:
                print("Telegram: sent")
        except Exception as e:
            print("Error:", e)

        if not args.loop:
            break
        time.sleep(max(1, args.interval))

if __name__ == "__main__":
    main()
