import logging

import yfinance as yf
import pandas_ta as ta
import pandas as pd

def analyze_trend(symbol, window=10):
    df = yf.Ticker(symbol).history(period='60d')
    if df.shape[0] < 30:
        return symbol, []

    df['ema7'] = ta.ema(df['Close'], length=7)
    macd = ta.macd(df['Close'])
    df = df.join(macd)
    df['adx'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']

    trends = []

    for i in range(-window, 0):  # 最近 N 天
        row = df.iloc[i]
        if pd.isna(row['MACD_12_26_9']) or pd.isna(row['MACDs_12_26_9']) or pd.isna(row['ema7']) or pd.isna(row['adx']):
            trends.append("unknown")
            continue

        cond_ema = row['Close'] > row['ema7']
        cond_macd = row['MACD_12_26_9'] > row['MACDs_12_26_9'] and row['MACD_12_26_9'] > 0
        cond_adx = row['adx'] > 25

        if cond_ema and cond_macd and cond_adx:
            trends.append("up")
        elif not cond_ema and not cond_macd and cond_adx:
            trends.append("down")
        else:
            trends.append("flat")

    logging.info(f"symbol: {symbol}, trends: {trends}")
    return symbol, trends
