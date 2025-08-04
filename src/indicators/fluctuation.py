from dataclasses import dataclass
from typing import Tuple, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

@dataclass
class FluctuationAnalysisResult:
    """
    封装股票价格波动分析的结果。
    """
    symbol: str
    initial_price: float
    current_price: float
    percentage_change: float
    change_type: str # "上涨" 或 "下跌"

class FluctuationAnalyzer:
    """
    负责分析股票价格波动。
    """

    @staticmethod
    def analyze_fluctuation(
        symbol: str,
        price_history: deque[Tuple[datetime, float]],
        current_price: float,
        time_window_minutes: int = 1
    ) -> Optional[FluctuationAnalysisResult]:
        """
        分析股票在指定时间窗口内的价格波动。
        :param symbol: 股票代码
        :param price_history: 包含 (timestamp, price) 元组的 deque
        :param current_price: 当前实时价格
        :param time_window_minutes: 价格比较的时间窗口（分钟）
        :return: FluctuationAnalysisResult 对象，如果数据不足则返回 None
        """
        now = datetime.now()

        # 确保有足够的数据点进行比较
        if len(price_history) < 2:
            logging.debug(f"{symbol}: 历史数据点不足，无法分析波动。")
            return None

        # 找到 time_window_minutes 分钟前的价格
        initial_price_entry = None
        for i in range(len(price_history) - 1, -1, -1):
            timestamp, price = price_history[i]
            if now - timestamp >= timedelta(minutes=time_window_minutes):
                initial_price_entry = (timestamp, price)
                break

        if initial_price_entry is None:
            logging.debug(f"{symbol}: 尚未收集到足够 {time_window_minutes} 分钟前的价格数据。")
            return None

        initial_price = initial_price_entry[1]

        if initial_price == 0: # 避免除以零
            logging.warning(f"{symbol}: 初始价格为零，无法计算波动。")
            return None

        percentage_change = ((current_price - initial_price) / initial_price) * 100
        change_type = "上涨" if percentage_change > 0 else "下跌"

        return FluctuationAnalysisResult(
            symbol=symbol,
            initial_price=initial_price,
            current_price=current_price,
            percentage_change=percentage_change,
            change_type=change_type
        )