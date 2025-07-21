import logging
from dataclasses import dataclass
from typing import List, Optional

import yfinance as yf
import pandas_ta as ta
import pandas as pd

@dataclass
class IndicatorSnapshot:
    ema7: float         # 7日指数移动平均线（短期趋势）
    ema20: float        # 20日指数移动平均线（中期趋势）

    macd: float         # MACD DIF（快线）
    macd_signal: float  # MACD DEA（慢线/信号线）
    macd_hist: float    # MACD 柱状图（快线 - 慢线，用于动能判断）

    adx: float          # ADX 趋势强度指标（无方向性，仅强度）
    plus_di: float      # ADX 的 +DI，表示上涨趋势强度
    minus_di: float     # ADX 的 -DI，表示下跌趋势强度

    bb_upper: float     # 布林带上轨（价格上限）
    bb_middle: float    # 布林带中轨（一般为 20 日 SMA）
    bb_lower: float     # 布林带下轨（价格下限）

    rsi: float          # 新增 RSI

    close: float        # 最新收盘价（用于参考）

@dataclass
class TrendAnalysisResult:
    symbol: str                     # 股票代码
    trends: List[str]               # 最近 N 日的趋势判断（例如 ["up", "flat", "down", ...]）
    indicators: Optional[IndicatorSnapshot] = None  # 技术指标快照（最近一天）
    error: Optional[str] = None     # 如果分析失败，这里记录错误信息
    signal: Optional[str] = None  # 新增


def analyze_trend(symbol: str, window: int = 10, adx_threshold: float = 25,
                  min_consecutive_days: int = 3) -> TrendAnalysisResult:
    try:
        df = yf.Ticker(symbol).history(period='90d', interval='1d')
        if df.shape[0] < window + 30:
            logging.warning(f"{symbol} 数据不足")
            return TrendAnalysisResult(symbol=symbol, trends=[], error="数据不足")

        # === 指标计算 ===
        df['ema7'] = ta.ema(df['Close'], length=7)
        df['ema20'] = ta.ema(df['Close'], length=20)

        macd = ta.macd(df['Close'])
        df = df.join(macd)

        adx = ta.adx(df['High'], df['Low'], df['Close'])
        df[['adx', 'plus_di', 'minus_di']] = adx[['ADX_14', 'DMP_14', 'DMN_14']]

        bb = ta.bbands(df['Close'], length=20, std=2.0)
        df = df.join(bb)

        df['rsi'] = ta.rsi(df['Close'], length=14)

        df.dropna(inplace=True)
        df = df.tail(window)

        # === 判断条件 ===
        cond_ema_up = df['ema7'] > df['ema20']
        cond_ema_down = df['ema7'] < df['ema20']

        cond_macd_up = (df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACDh_12_26_9'].diff() > 0)
        cond_macd_down = (df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACDh_12_26_9'].diff() < 0)

        cond_adx_up = (df['adx'] > adx_threshold) & (df['plus_di'] > df['minus_di'])
        cond_adx_down = (df['adx'] > adx_threshold) & (df['plus_di'] < df['minus_di'])

        cond_bb_up = df['Close'] > df['BBM_20_2.0']
        cond_bb_down = df['Close'] < df['BBM_20_2.0']
        cond_bb_valid = (df['Close'] < df['BBU_20_2.0']) & (df['Close'] > df['BBL_20_2.0'])

        cond_rsi_not_overbought = df['rsi'] < 70
        cond_rsi_not_oversold = df['rsi'] > 30

        cond_up = (cond_ema_up & cond_macd_up & cond_adx_up &
                   cond_bb_up & cond_bb_valid & cond_rsi_not_overbought)

        cond_down = (cond_ema_down & cond_macd_down & cond_adx_down &
                     cond_bb_down & cond_bb_valid & cond_rsi_not_oversold)

        # === 生成趋势列表 ===
        trends = []
        for i in range(len(df)):
            if cond_up.iloc[i]:
                trends.append("up")
            elif cond_down.iloc[i]:
                trends.append("down")
            else:
                trends.append("flat")

        # === 连续趋势判断生成 signal ===
        def check_consecutive(trend_list: List[str], trend_type: str, n: int) -> bool:
            return trend_list[-n:] == [trend_type] * n

        signal = "hold"
        if len(trends) >= min_consecutive_days:
            if check_consecutive(trends, "up", min_consecutive_days):
                signal = "buy"
            elif check_consecutive(trends, "down", min_consecutive_days):
                signal = "sell"

        # === 构建快照 ===
        latest = df.iloc[-1]
        snapshot = IndicatorSnapshot(
            ema7=latest['ema7'],
            ema20=latest['ema20'],
            macd=latest['MACD_12_26_9'],
            macd_signal=latest['MACDs_12_26_9'],
            macd_hist=latest['MACDh_12_26_9'],
            adx=latest['adx'],
            plus_di=latest['plus_di'],
            minus_di=latest['minus_di'],
            bb_upper=latest['BBU_20_2.0'],
            bb_middle=latest['BBM_20_2.0'],
            bb_lower=latest['BBL_20_2.0'],
            close=latest['Close'],
            rsi=latest['rsi']
        )

        logging.info(f"[{symbol}] 趋势: {trends}, Signal: {signal}, 收盘: {latest['Close']:.2f}")
        return TrendAnalysisResult(symbol=symbol, trends=trends, indicators=snapshot, signal=signal)

    except Exception as e:
        logging.error(f"[{symbol}] 趋势分析失败: {str(e)}")
        return TrendAnalysisResult(symbol=symbol, trends=[], error=str(e))
