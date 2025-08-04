import logging
from dataclasses import dataclass
from typing import List, Optional

import yfinance as yf
import pandas_ta as ta

from ..config.config_manager import get_trend_analysis_config, TrendAnalysisConfig

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


def analyze_trend(symbol: str, window: int = 10, user_email: str = None,
                  config: TrendAnalysisConfig = None) -> TrendAnalysisResult:
    try:
        # 获取配置参数
        if config is None:
            config = get_trend_analysis_config(user_email)
        
        df = yf.Ticker(symbol).history(period='90d', interval='1d')
        if df.shape[0] < window + 30:
            logging.warning(f"{symbol} 数据不足")
            return TrendAnalysisResult(symbol=symbol, trends=[], error="数据不足")

        # === 使用配置的指标参数计算 ===
        df['ema7'] = ta.ema(df['Close'], length=config.ema_short_period)
        df['ema20'] = ta.ema(df['Close'], length=config.ema_long_period)

        macd = ta.macd(df['Close'], fast=config.macd_fast_period, 
                      slow=config.macd_slow_period, signal=config.macd_signal_period)
        df = df.join(macd)

        adx = ta.adx(df['High'], df['Low'], df['Close'], length=config.adx_period)
        df[['adx', 'plus_di', 'minus_di']] = adx[[f'ADX_{config.adx_period}', f'DMP_{config.adx_period}', f'DMN_{config.adx_period}']]

        bb = ta.bbands(df['Close'], length=config.bb_period, std=config.bb_std_dev)
        df = df.join(bb)

        df['rsi'] = ta.rsi(df['Close'], length=config.rsi_period)

        df.dropna(inplace=True)
        df = df.tail(window)

        # === 判断条件 (量化为分数) ===
        # Initialize score columns
        df['up_score'] = 0
        df['down_score'] = 0

        # EMA Score
        df['up_score'] += (df['ema7'] > df['ema20']).astype(int)
        df['down_score'] += (df['ema7'] < df['ema20']).astype(int)

        # MACD Score - 使用动态列名
        macd_col = f'MACD_{config.macd_fast_period}_{config.macd_slow_period}_{config.macd_signal_period}'
        macd_signal_col = f'MACDs_{config.macd_fast_period}_{config.macd_slow_period}_{config.macd_signal_period}'
        macd_hist_col = f'MACDh_{config.macd_fast_period}_{config.macd_slow_period}_{config.macd_signal_period}'
        
        df['up_score'] += ((df[macd_col] > df[macd_signal_col]) & (df[macd_hist_col].diff() > 0)).astype(int)
        df['down_score'] += ((df[macd_col] < df[macd_signal_col]) & (df[macd_hist_col].diff() < 0)).astype(int)

        # ADX Score
        df['up_score'] += ((df['adx'] > config.adx_threshold) & (df['plus_di'] > df['minus_di'])).astype(int)
        df['down_score'] += ((df['adx'] > config.adx_threshold) & (df['plus_di'] < df['minus_di'])).astype(int)

        # Bollinger Bands Score - 使用动态列名
        bb_upper_col = f'BBU_{config.bb_period}_{config.bb_std_dev}'
        bb_middle_col = f'BBM_{config.bb_period}_{config.bb_std_dev}'
        bb_lower_col = f'BBL_{config.bb_period}_{config.bb_std_dev}'
        
        # For 'up': Close above middle band and within upper band
        df['up_score'] += ((df['Close'] > df[bb_middle_col]) & (df['Close'] < df[bb_upper_col])).astype(int)
        # For 'down': Close below middle band and within lower band
        df['down_score'] += ((df['Close'] < df[bb_middle_col]) & (df['Close'] > df[bb_lower_col])).astype(int)

        # RSI Score - 使用配置的阈值
        df['up_score'] += (df['rsi'] < config.rsi_overbought).astype(int) # Not overbought is a positive sign for 'up'
        df['down_score'] += (df['rsi'] > config.rsi_oversold).astype(int) # Not oversold is a positive sign for 'down'

        # === 生成趋势列表 ===
        trends = []
        for i in range(len(df)):
            current_up_score = df['up_score'].iloc[i]
            current_down_score = df['down_score'].iloc[i]

            if current_up_score >= config.up_trend_threshold and current_up_score > current_down_score:
                trends.append("up")
            elif current_down_score >= config.down_trend_threshold and current_down_score > current_up_score:
                trends.append("down")
            else:
                trends.append("flat")

        # === 信号判断 (基于加权分数和阈值) ===
        # Use weights from config
        weights = config.signal_weights

        # Calculate daily buy/sell scores
        df['buy_signal_score'] = 0.0
        df['sell_signal_score'] = 0.0

        # EMA contribution
        df['buy_signal_score'] += ((df['ema7'] > df['ema20']) * weights['ema_cross'])
        df['sell_signal_score'] += ((df['ema7'] < df['ema20']) * weights['ema_cross'])

        # MACD contribution - 使用动态列名
        df['buy_signal_score'] += ((df[macd_col] > df[macd_signal_col]) & (df[macd_hist_col] > 0)) * weights['macd_cross']
        df['sell_signal_score'] += ((df[macd_col] < df[macd_signal_col]) & (df[macd_hist_col] < 0)) * weights['macd_cross']

        # ADX contribution (only if ADX indicates strong trend)
        df['buy_signal_score'] += ((df['adx'] > config.adx_threshold) & (df['plus_di'] > df['minus_di'])) * weights['adx_strength']
        df['sell_signal_score'] += ((df['adx'] > config.adx_threshold) & (df['plus_di'] < df['minus_di'])) * weights['adx_strength']

        # Bollinger Bands contribution - 使用动态列名
        # Buy: Close above middle band, approaching lower band (rebound) or breaking upper band (strong momentum)
        df['buy_signal_score'] += ((df['Close'] > df[bb_middle_col]) | (df['Close'] < df[bb_lower_col])) * weights['bb_position']
        # Sell: Close below middle band, approaching upper band (rejection) or breaking lower band (strong momentum)
        df['sell_signal_score'] += ((df['Close'] < df[bb_middle_col]) | (df['Close'] > df[bb_upper_col])) * weights['bb_position']

        # RSI contribution - 使用配置的阈值
        df['buy_signal_score'] += (df['rsi'] < config.rsi_oversold) * weights['rsi_level'] # Oversold
        df['sell_signal_score'] += (df['rsi'] > config.rsi_overbought) * weights['rsi_level'] # Overbought

        # Use signal thresholds from config
        buy_threshold = config.buy_signal_threshold
        sell_threshold = config.sell_signal_threshold

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
            macd=latest[macd_col],
            macd_signal=latest[macd_signal_col],
            macd_hist=latest[macd_hist_col],
            adx=latest['adx'],
            plus_di=latest['plus_di'],
            minus_di=latest['minus_di'],
            bb_upper=latest[bb_upper_col],
            bb_middle=latest[bb_middle_col],
            bb_lower=latest[bb_lower_col],
            close=latest['Close'],
            rsi=latest['rsi']
        )

        logging.info(f"[{symbol}] 趋势: {trends}, Signal: {signal}, Buy Score: {latest_buy_score:.2f}, Sell Score: {latest_sell_score:.2f}, 收盘: {latest['Close']:.2f}")
        return TrendAnalysisResult(symbol=symbol, trends=trends, indicators=snapshot, signal=signal)

    except Exception as e:
        logging.error(f"[{symbol}] 趋势分析失败: {str(e)}")
        return TrendAnalysisResult(symbol=symbol, trends=[], error=str(e))
