import logging
import yfinance as yf
import pandas_ta as ta
import pandas as pd

def analyze_trend(symbol: str, window: int = 10,
                  adx_threshold: float = 25) -> tuple[str, list[str]]:
    try:
        df = yf.Ticker(symbol).history(period='90d', interval='1d')
        if df.shape[0] < window + 20:  # 至少需要指标计算窗口 + window
            logging.warning(f"{symbol} 数据不足")
            return symbol, []

        # 计算指标（向量化）
        df['ema7'] = ta.ema(df['Close'], length=7)
        macd = ta.macd(df['Close'])
        df = df.join(macd)
        df['adx'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']

        df.dropna(inplace=True)  # 去掉计算指标后的 NaN 行
        df = df.tail(window)

        # 判定逻辑向量化
        cond_ema = df['Close'] > df['ema7']
        cond_macd = (df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACD_12_26_9'] > 0)
        cond_adx = df['adx'] > adx_threshold

        cond_up = cond_ema & cond_macd & cond_adx
        cond_down = (~cond_ema) & (~cond_macd) & cond_adx

        trends = []
        for i in range(len(df)):
            if cond_up.iloc[i]:
                trends.append("up")
            elif cond_down.iloc[i]:
                trends.append("down")
            else:
                trends.append("flat")

        logging.info(f"[{symbol}] 最近{window}日趋势: {trends}")
        return symbol, trends

    except Exception as e:
        logging.error(f"[{symbol}] 趋势分析失败: {str(e)}")
        return symbol, []
