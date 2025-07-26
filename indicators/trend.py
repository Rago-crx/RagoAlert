import logging
from dataclasses import dataclass
from typing import List, Optional

import yfinance as yf
import pandas_ta as ta

from config import UP_TREND_THRESHOLD, DOWN_TREND_THRESHOLD, SIGNAL_WEIGHTS, BUY_SIGNAL_THRESHOLD, SELL_SIGNAL_THRESHOLD

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
    bb_lower: float     # 布林带下限）

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

        # === 判断条件 (量化为分数) ===
        # Initialize score columns
        df['up_score'] = 0
        df['down_score'] = 0

        # EMA Score
        df['up_score'] += (df['ema7'] > df['ema20']).astype(int)
        df['down_score'] += (df['ema7'] < df['ema20']).astype(int)

        # MACD Score
        df['up_score'] += ((df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACDh_12_26_9'].diff() > 0)).astype(int)
        df['down_score'] += ((df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACDh_12_26_9'].diff() < 0)).astype(int)

        # ADX Score
        df['up_score'] += ((df['adx'] > adx_threshold) & (df['plus_di'] > df['minus_di'])).astype(int)
        df['down_score'] += ((df['adx'] > adx_threshold) & (df['plus_di'] < df['minus_di'])).astype(int)

        # Bollinger Bands Score
        # For 'up': Close above middle band and within upper band
        df['up_score'] += ((df['Close'] > df['BBM_20_2.0']) & (df['Close'] < df['BBU_20_2.0'])).astype(int)
        # For 'down': Close below middle band and within lower band
        df['down_score'] += ((df['Close'] < df['BBM_20_2.0']) & (df['Close'] > df['BBL_20_2.0'])).astype(int)

        # RSI Score
        df['up_score'] += (df['rsi'] < 70).astype(int) # Not overbought is a positive sign for 'up'
        df['down_score'] += (df['rsi'] > 30).astype(int) # Not oversold is a positive sign for 'down'

        # === 生成趋势列表 ===
        trends = []
        for i in range(len(df)):
            current_up_score = df['up_score'].iloc[i]
            current_down_score = df['down_score'].iloc[i]

            if current_up_score >= UP_TREND_THRESHOLD and current_up_score > current_down_score:
                trends.append("up")
            elif current_down_score >= DOWN_TREND_THRESHOLD and current_down_score > current_up_score:
                trends.append("down")
            else:
                trends.append("flat")

        # === 信号判断 (基于加权分数和阈值) ===
        # Use weights from config.py
        weights = SIGNAL_WEIGHTS

        # Calculate daily buy/sell scores
        df['buy_signal_score'] = 0.0
        df['sell_signal_score'] = 0.0

        # EMA contribution
        df['buy_signal_score'] += ((df['ema7'] > df['ema20']) * weights['ema_cross'])
        df['sell_signal_score'] += ((df['ema7'] < df['ema20']) * weights['ema_cross'])

        # MACD contribution
        df['buy_signal_score'] += ((df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACDh_12_26_9'] > 0)) * weights['macd_cross']
        df['sell_signal_score'] += ((df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACDh_12_26_9'] < 0)) * weights['macd_cross']

        # ADX contribution (only if ADX indicates strong trend)
        df['buy_signal_score'] += ((df['adx'] > adx_threshold) & (df['plus_di'] > df['minus_di'])) * weights['adx_strength']
        df['sell_signal_score'] += ((df['adx'] > adx_threshold) & (df['plus_di'] < df['minus_di'])) * weights['adx_strength']

        # Bollinger Bands contribution
        # Buy: Close above middle band, approaching lower band (rebound) or breaking upper band (strong momentum)
        df['buy_signal_score'] += ((df['Close'] > df['BBM_20_2.0']) | (df['Close'] < df['BBL_20_2.0'])) * weights['bb_position']
        # Sell: Close below middle band, approaching upper band (rejection) or breaking lower band (strong momentum)
        df['sell_signal_score'] += ((df['Close'] < df['BBM_20_2.0']) | (df['Close'] > df['BBU_20_2.0'])) * weights['bb_position']

        # RSI contribution
        df['buy_signal_score'] += (df['rsi'] < 30) * weights['rsi_level'] # Oversold
        df['sell_signal_score'] += (df['rsi'] > 70) * weights['rsi_level'] # Overbought

        # Use signal thresholds from config.py
        buy_threshold = BUY_SIGNAL_THRESHOLD
        sell_threshold = SELL_SIGNAL_THRESHOLD

        latest_buy_score = df['buy_signal_score'].iloc[-1]
        latest_sell_score = df['sell_signal_score'].iloc[-1]

        if latest_buy_score >= buy_threshold and latest_buy_score > latest_sell_score:
            signal = "buy"
        elif latest_sell_score >= sell_threshold and latest_sell_score > latest_buy_score:
            signal = "sell"
        else:
            signal = "hold" # Default or if scores are not decisive

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

        logging.info(f"[{symbol}] 趋势: {trends}, Signal: {signal}, Buy Score: {latest_buy_score:.2f}, Sell Score: {latest_sell_score:.2f}, 收盘: {latest['Close']:.2f}")
        return TrendAnalysisResult(symbol=symbol, trends=trends, indicators=snapshot, signal=signal)

    except Exception as e:
        logging.error(f"[{symbol}] 趋势分析失败: {str(e)}")
        return TrendAnalysisResult(symbol=symbol, trends=[], error=str(e))
