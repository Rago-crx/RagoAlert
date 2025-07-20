from collections import Counter

from data.yahoo import get_top_nasdaq_by_volume
from config import CHINA_TECH
from indicators.trend import analyze_trend  # 需要返回趋势序列

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


def detect_trend_change(trend_list, window=3):
    """
    检测最近 window 天内是否发生趋势变化。
    返回（变化前的趋势，当前趋势）或 None
    """
    if len(trend_list) < window:
        return None

    recent_trends = trend_list[-window:]

    # 如果三天趋势都一样，则无变化
    if len(set(recent_trends)) == 1:
        return None

    # 返回最近一次变化：找最后不同的两个连续趋势
    for i in range(-window + 1, 0):
        if recent_trends[i] != recent_trends[i - 1]:
            return recent_trends[i - 1], recent_trends[i]

    # 如果趋势有变化但不是连续的，也返回前后最频繁趋势
    trend_count = Counter(recent_trends)
    common = trend_count.most_common(2)
    if len(common) >= 2:
        return common[1][0], common[0][0]

    return None


def monitor():
    tickers = get_top_nasdaq_by_volume() + CHINA_TECH

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(analyze_trend, sym): sym for sym in tickers}
        for future in as_completed(futures):
            symbol, trend_list = future.result()
            if not trend_list:
                continue

            change = detect_trend_change(trend_list)
            if change:
                prev, curr = change
                logging.info(f"{symbol} 趋势变化：{prev} -> {curr}")
            else:
                logging.info(f"{symbol} 趋势维持：{trend_list[-1]}")
