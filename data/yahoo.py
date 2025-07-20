import yfinance as yf
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import NASDAQ_SYMBOLS

def fetch_volume(symbol):
    try:
        data = yf.Ticker(symbol).history(period='1d')
        if not data.empty:
            return symbol, data['Volume'].iloc[-1]
    except Exception as e:
        logging.warning(f"Failed to get volume for {symbol}: {e}")
    return symbol, 0

def get_top_nasdaq_by_volume(n=20):
    volumes = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_volume, sym): sym for sym in NASDAQ_SYMBOLS}
        for future in as_completed(futures):
            symbol, volume = future.result()
            volumes[symbol] = volume
    sorted_volumes = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
    return [symbol for symbol, vol in sorted_volumes[:n]]
