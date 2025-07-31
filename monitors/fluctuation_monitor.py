import logging
import time
from datetime import datetime, timedelta
from typing import Dict
from collections import deque

from config import FLUCTUATION_THRESHOLD_PERCENT, FLUCTUATION_MONITOR_SYMBOLS, recipients
from data.yahoo import get_current_price
from notifiers.email import send_gmail, build_fluctuation_email_content
from indicators.fluctuation import FluctuationAnalyzer, FluctuationAnalysisResult # 导入新创建的类


class FluctuationMonitor:
    # 存储每个股票的历史价格，使用 deque 限制存储数量
    # key: symbol, value: deque of (timestamp, price)
    _price_history: Dict[str, deque] = {}
    _last_notification_time: Dict[str, datetime] = {} # 记录上次发送通知的时间，避免频繁发送

    @staticmethod
    def _is_us_market_open_or_pre_post() -> bool:
        """
        判断当前时间是否在美股交易时段（包括盘前盘后）内。
        美股常规交易时间：美东时间 9:30 AM - 4:00 PM
        盘前：美东时间 4:00 AM - 9:30 AM
        盘后：美东时间 4:00 PM - 8:00 PM
        转换为北京时间：
        美东时间 = 北京时间 - 12小时 (夏令时) 或 -13小时 (冬令时)
        假设当前为夏令时（3月第二个周日至11月第一个周日）：
        盘前：北京时间 16:00 - 21:30
        盘中：北京时间 21:30 - 次日 04:00
        盘后：北京时间 04:00 - 08:00
        """
        now_utc = datetime.utcnow()
        # 简单判断是否在夏令时期间（通常3月到11月）
        # 更精确的判断需要考虑时区库，例如 pytz
        is_daylight_saving = 3 <= now_utc.month <= 10 # 简化判断

        if is_daylight_saving:
            # 夏令时：美东时间 = UTC - 4小时
            # 盘前：UTC 8:00 - 13:30
            # 盘中：UTC 13:30 - 20:00
            # 盘后：UTC 20:00 - 00:00 (次日)
            market_open_utc = now_utc.replace(hour=13, minute=30, second=0, microsecond=0)
            market_close_utc = now_utc.replace(hour=20, minute=0, second=0, microsecond=0)
            pre_market_open_utc = now_utc.replace(hour=8, minute=0, second=0, microsecond=0)
            post_market_close_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) # 次日0点

        else:
            # 冬令时：美东时间 = UTC - 5小时
            # 盘前：UTC 9:00 - 14:30
            # 盘中：UTC 14:30 - 21:00
            # 盘后：UTC 21:00 - 01:00 (次日)
            market_open_utc = now_utc.replace(hour=14, minute=30, second=0, microsecond=0)
            market_close_utc = now_utc.replace(hour=21, minute=0, second=0, microsecond=0)
            pre_market_open_utc = now_utc.replace(hour=9, minute=0, second=0, microsecond=0)
            post_market_close_utc = now_utc.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1) # 次日1点

        # 检查是否在周一到周五
        if now_utc.weekday() >= 5: # Saturday is 5, Sunday is 6
            return False

        # 检查是否在交易时段内
        if (pre_market_open_utc <= now_utc < market_open_utc) or \
           (market_open_utc <= now_utc < market_close_utc) or \
           (market_close_utc <= now_utc < post_market_close_utc):
            logging.info(f"当前时间 {now_utc.strftime('%H:%M:%S UTC')} 在美股交易时段内。")
            return True
        else:
            logging.info(f"当前时间 {now_utc.strftime('%H:%M:%S UTC')} 不在美股交易时段内。")
            return False

    @staticmethod
    def run():
        """
        运行股票价格波动监控。
        每分钟获取一次价格，并检测波动。
        """
        logging.info("启动股票价格波动监控...")
        # 初始化价格历史
        for symbol in FLUCTUATION_MONITOR_SYMBOLS:
            FluctuationMonitor._price_history[symbol] = deque(maxlen=60)  # 存储最近60分钟的价格
            FluctuationMonitor._last_notification_time[symbol] = datetime.min # 初始化为最小时间

        while True:
            if not FluctuationMonitor._is_us_market_open_or_pre_post():
                logging.info("当前不在美股交易时段，等待下一分钟...")
                time.sleep(60) # 等待一分钟
                continue

            fluctuation_results_to_notify = [] # Step 1: Collect results for a single email

            for symbol in FLUCTUATION_MONITOR_SYMBOLS:
                current_price = get_current_price(symbol)
                if current_price == 0.0:
                    logging.warning(f"无法获取 {symbol} 的实时价格，跳过。")
                    continue

                now = datetime.now()
                FluctuationMonitor._price_history[symbol].append((now, current_price))

                # 调用 FluctuationAnalyzer 进行波动分析
                analysis_result: FluctuationAnalysisResult | None = FluctuationAnalyzer.analyze_fluctuation(
                    symbol=symbol,
                    price_history=FluctuationMonitor._price_history[symbol],
                    current_price=current_price,
                    time_window_minutes=1 # 过去一分钟的波动
                )

                if analysis_result is None:
                    logging.info(f"{symbol}: 波动分析数据不足，跳过。")
                    continue

                # 检查是否达到波动阈值
                if abs(analysis_result.percentage_change) >= FLUCTUATION_THRESHOLD_PERCENT:
                    # 检查是否在短时间内重复发送通知
                    last_notif_time = FluctuationMonitor._last_notification_time.get(symbol, datetime.min)
                    if now - last_notif_time < timedelta(minutes=5): # 5分钟内不再重复发送
                        logging.info(f"{symbol}: 波动达到阈值，但距离上次通知不足5分钟，跳过发送。")
                        continue

                    fluctuation_results_to_notify.append(analysis_result) # Step 1: Add to list
                    FluctuationMonitor._last_notification_time[symbol] = now # Update notification time for this symbol
                    logging.info(f"{symbol}: 价格在过去一分钟内 {analysis_result.change_type} {analysis_result.percentage_change:.2f}%，已标记待发送。")
                else:
                    logging.info(f"{symbol}: 价格波动 {analysis_result.percentage_change:.2f}%，未达到阈值。")

            # Step 1: Send a single email if there are any fluctuations to report
            if fluctuation_results_to_notify:
                subject = "🚨 股票波动提醒"
                html_body = build_fluctuation_email_content(fluctuation_results_to_notify) # Step 2: Pass list to email content builder
                send_gmail(subject, html_body, recipients)
                logging.info(f"已发送包含 {len(fluctuation_results_to_notify)} 支股票波动信息的邮件。")

            time.sleep(60)  # 每分钟运行一次