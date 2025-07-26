import yfinance as yf
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
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

def get_historical_data(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    从 Yahoo Finance 获取指定股票的历史数据。
    :param symbol: 股票代码
    :param period: 数据周期 (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
    :param interval: 数据间隔 (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
    :return: 包含历史数据的 Pandas DataFrame
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            logging.warning(f"未找到 {symbol} 的历史数据，或数据为空。")
        return data
    except Exception as e:
        logging.error(f"获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()

def get_current_price(symbol: str) -> float:
    """
    获取指定股票的实时价格。
    注意：yfinance 的实时数据可能不是严格的实时，而是有延迟的。
    对于高频监控，可能需要更专业的实时数据API。
    """
    try:
        ticker = yf.Ticker(symbol)
        # 使用 fast_info 获取最新价格，通常比 history(period='1m', interval='1m') 更快
        # 但 fast_info 可能不包含所有信息，且其 "last_price" 字段可能不是严格的实时交易价格
        # 对于盘中实时价格，通常需要查询 'regularMarketPrice' 或 'currentPrice'
        info = ticker.fast_info
        price = info.last_price # 或者 info.regularMarketPrice
        if price:
            logging.info(f"获取 {symbol} 实时价格: {price}")
            return price
        else:
            logging.warning(f"未获取到 {symbol} 的实时价格。")
            return 0.0
    except Exception as e:
        logging.error(f"获取 {symbol} 实时价格失败: {e}")
        return 0.0
