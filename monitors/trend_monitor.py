from data.yahoo import get_top_nasdaq_by_volume
from config import CHINA_TECH, recipients
from indicators.trend import analyze_trend, TrendAnalysisResult
from notifiers.email import send_gmail, build_trend_email_content
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple
import logging
from datetime import datetime, timedelta # 导入 datetime 和 timedelta


class TrendMonitor:
    @staticmethod
    def detect_trend_change(trend_list, window=2):
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

    @staticmethod
    def _is_us_market_time(target_hour_utc: int, target_minute_utc: int, tolerance_minutes: int = 5) -> bool:
        """
        检查当前 UTC 时间是否在指定的美股交易相关时间点附近。
        :param target_hour_utc: 目标 UTC 小时
        :param target_minute_utc: 目标 UTC 分钟
        :param tolerance_minutes: 允许的误差分钟数
        :return: 如果在指定时间点附近，则返回 True
        """
        now_utc = datetime.utcnow()
        target_time_utc = now_utc.replace(hour=target_hour_utc, minute=target_minute_utc, second=0, microsecond=0)

        # 检查是否在周一到周五
        if now_utc.weekday() >= 5: # Saturday is 5, Sunday is 6
            logging.info("当前是周末，不执行趋势监控。")
            return False

        # 检查当前时间是否在目标时间点的容忍范围内
        if abs((now_utc - target_time_utc).total_seconds()) <= tolerance_minutes * 60:
            logging.info(f"当前时间 {now_utc.strftime('%H:%M:%S UTC')} 在目标执行时间 {target_time_utc.strftime('%H:%M:%S UTC')} 附近。")
            return True
        else:
            logging.info(f"当前时间 {now_utc.strftime('%H:%M:%S UTC')} 不在目标执行时间 {target_time_utc.strftime('%H:%M:%S UTC')} 附近。")
            return False

    # 记录上次执行趋势监控的时间，避免在同一时间段内重复执行
    _last_run_time: Dict[str, datetime] = {
        "pre_market": datetime.min,
        "post_market": datetime.min
    }

    @staticmethod
    def run(time_check=True):
        """
        运行股票趋势监控。
        此方法设计为由外部调度器在特定时间点调用。
        """
        now = datetime.utcnow()

        # 美股盘前执行时间 (例如美东时间 9:00 AM)
        # 夏令时 (UTC-4): UTC 13:00
        # 冬令时 (UTC-5): UTC 14:00
        is_daylight_saving = 3 <= now.month <= 10 # 简化判断
        pre_market_hour_utc = 13 if is_daylight_saving else 14

        # 美股盘后执行时间 (例如美东时间 5:00 PM)
        # 夏令时 (UTC-4): UTC 21:00
        # 冬令时 (UTC-5): UTC 22:00
        post_market_hour_utc = 21 if is_daylight_saving else 22
        if not time_check:
            logging.info("检测到跳过时间检测，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["pre_market"] = now
            return

        # 检查是否是盘前执行时间点
        if TrendMonitor._is_us_market_time(pre_market_hour_utc, 0) and \
           (now - TrendMonitor._last_run_time["pre_market"]) > timedelta(hours=23): # 确保每天只运行一次
            logging.info("检测到美股盘前执行时间，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["pre_market"] = now
            return # 执行完毕后退出，等待下次调度

        # 检查是否是盘后执行时间点
        if TrendMonitor._is_us_market_time(post_market_hour_utc, 0) and \
           (now - TrendMonitor._last_run_time["post_market"]) > timedelta(hours=23): # 确保每天只运行一次
            logging.info("检测到美股盘后执行时间，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["post_market"] = now
            return # 执行完毕后退出，等待下次调度

        logging.info("当前时间不在趋势监控的执行时间点内。")

if __name__ == '__main__':
    TrendMonitor.run(time_check=False)

