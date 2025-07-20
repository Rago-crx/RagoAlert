from data.yahoo import get_top_nasdaq_by_volume
from config import CHINA_TECH, recipients
from indicators.trend import analyze_trend
from notifiers.email import send_gmail, build_trend_email_content
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple
import logging


def detect_trend_change(trend_list, window=3):
    """
    检测最近 window 天内是否发生趋势变化。
    返回（变化前的趋势，当前趋势）或 None
    """
    if len(trend_list) < window:
        return None

    recent = trend_list[-window:]
    if len(set(recent)) == 1:
        return None

    for i in range(-window + 1, 0):
        if recent[i] != recent[i - 1]:
            return recent[i - 1], recent[i]
    return None


def monitor():
    tickers = get_top_nasdaq_by_volume() + CHINA_TECH
    logging.info(f"监控以下股票: {tickers}")

    trends: Dict[str, str] = {}
    changes: Dict[str, Tuple[str, str]] = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(analyze_trend, sym): sym for sym in tickers}
        for future in as_completed(futures):
            symbol, trend_list = future.result()
            if not trend_list or len(trend_list) < 2:
                continue

            current_trend = trend_list[-1]
            trends[symbol] = current_trend

            change = detect_trend_change(trend_list)
            if change:
                changes[symbol] = change
                logging.info(f"{symbol} 趋势变化: {change[0]} → {change[1]}")
            else:
                logging.info(f"{symbol} 趋势未变: {current_trend}")

    if trends:
        subject = "📊 股票趋势日报"
        html_body = build_trend_email_content(trends, changes)
        _recipients = recipients
        send_gmail(subject, html_body, _recipients)
