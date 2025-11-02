# Crypto Spot+Futures Signal (RSI/MFI/Volume/Basis/OI/Funding)

Скрипт анализирует спот и фьючерсы: RSI, MFI, OBV, базис (fut-spot), фандинг, OI; выдаёт BUY/SELL/NEUTRAL.

Быстрый старт:
1) Python 3.10+
2) python -m venv .venv && activate
3) pip install -r requirements.txt
4) cp .env.example .env (заполните при необходимости TELEGRAM_*)
5) python main.py --symbol BTC/USDT --timeframe 5m --lookback 500
