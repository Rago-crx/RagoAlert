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
        """
        now_utc = datetime.utcnow()
        target_time_utc = now_utc.replace(hour=target_hour_utc, minute=target_minute_utc, second=0, microsecond=0)

        if now_utc.weekday() >= 5:  # 周末不执行
            logging.info("当前是周末，不执行趋势监控。")
            return False

        return abs((now_utc - target_time_utc).total_seconds()) <= tolerance_minutes * 60

    _last_run_time: Dict[str, datetime] = {
        "pre_market": datetime.min,
        "post_market": datetime.min
    }

    @staticmethod
    def _execute_trend_analysis():
        """
        核心执行逻辑：分析趋势、检测变化、发送邮件
        """
        tickers = get_top_nasdaq_by_volume() + CHINA_TECH
        logging.info(f"监控以下股票: {tickers}")

        trends: Dict[str, str] = {}
        changes: Dict[str, Tuple[str, str]] = {}
        results: Dict[str, TrendAnalysisResult] = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(analyze_trend, sym): sym for sym in tickers}
            for future in as_completed(futures):
                result: TrendAnalysisResult = future.result()
                symbol = result.symbol
    
                if not result.trends or len(result.trends) < 2:
                    continue
    
                current_trend = result.trends[-1]
                trends[symbol] = current_trend
                results[symbol] = result
    
                change = TrendMonitor.detect_trend_change(result.trends)
                if change:
                    changes[symbol] = change
                    logging.info(f"{symbol} 趋势变化: {change[0]} → {change[1]}")
                else:
                    logging.info(f"{symbol} 趋势未变: {current_trend}")
    
        if trends:
            subject = "📊 股票趋势日报"
            html_body = build_trend_email_content(results, changes)  # 传入完整结果对象
            send_gmail(subject, html_body, recipients)

    @staticmethod
    def run(time_check=True):
        now = datetime.utcnow()
        is_daylight_saving = 3 <= now.month <= 10
        pre_market_hour_utc = 13 if is_daylight_saving else 14
        post_market_hour_utc = 21 if is_daylight_saving else 22

        if not time_check:
            logging.info("检测到跳过时间检测，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["pre_market"] = now
            return

        if TrendMonitor._is_us_market_time(pre_market_hour_utc, 0) and \
           (now - TrendMonitor._last_run_time["pre_market"]) > timedelta(hours=23):
            logging.info("检测到美股盘前执行时间，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["pre_market"] = now
            return

        if TrendMonitor._is_us_market_time(post_market_hour_utc, 0) and \
           (now - TrendMonitor._last_run_time["post_market"]) > timedelta(hours=23):
            logging.info("检测到美股盘后执行时间，开始趋势监控...")
            TrendMonitor._execute_trend_analysis()
            TrendMonitor._last_run_time["post_market"] = now
            return

        logging.info("当前时间不在趋势监控的执行时间点内。")

if __name__ == "__main__":
    TrendMonitor.run(time_check=False)

