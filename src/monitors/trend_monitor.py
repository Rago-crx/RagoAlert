"""
单用户趋势监控器
重构为只处理单个用户的趋势监控逻辑
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.config_manager import UserConfig, get_system_config
from ..data.yahoo import get_top_nasdaq_by_volume
from ..indicators.trend import analyze_trend, TrendAnalysisResult
from ..notifiers.email import send_gmail, build_trend_email_content


class TrendMonitor:
    """
    单用户趋势监控器
    负责监控单个用户配置的股票趋势变化
    """
    
    def __init__(self, user_config: UserConfig):
        """
        初始化趋势监控器
        
        Args:
            user_config: 用户配置对象
        """
        self.user_config = user_config
        # 记录该用户的上次执行时间
        self._last_run_time: Dict[str, datetime] = {
            "pre_market": datetime.min,
            "post_market": datetime.min
        }
        
        logging.info(f"初始化用户 {self.user_config.email} 的趋势监控器，监控股票: {self.user_config.trend.symbols}")
    
    def update_config(self, new_user_config: UserConfig):
        """
        更新用户配置
        
        Args:
            new_user_config: 新的用户配置
        """
        self.user_config = new_user_config
        logging.info(f"更新用户 {self.user_config.email} 的趋势监控配置")
    
    @staticmethod
    def detect_trend_change(trend_list: List[str], window: int = 2) -> Optional[Tuple[str, str]]:
        """
        检测最近 window 天内是否发生趋势变化
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
        检查当前 UTC 时间是否在指定的美股交易相关时间点附近
        """
        now_utc = datetime.utcnow()
        target_time_utc = now_utc.replace(hour=target_hour_utc, minute=target_minute_utc, second=0, microsecond=0)

        if now_utc.weekday() >= 5:  # 周末不执行
            return False

        return abs((now_utc - target_time_utc).total_seconds()) <= tolerance_minutes * 60
    
    def _should_run_analysis(self, market_session: str) -> bool:
        """
        判断是否应该执行趋势分析
        
        Args:
            market_session: 'pre_market' 或 'post_market'
            
        Returns:
            是否应该执行
        """
        now = datetime.utcnow()
        is_daylight_saving = 3 <= now.month <= 10
        
        if market_session == "pre_market":
            if not self.user_config.trend.pre_market_notification:
                return False
            target_hour = 13 if is_daylight_saving else 14
        elif market_session == "post_market":
            if not self.user_config.trend.post_market_notification:
                return False
            target_hour = 21 if is_daylight_saving else 22
        else:
            return False
        
        # 检查是否在目标时间附近
        if not self._is_us_market_time(target_hour, 0):
            return False
        
        # 检查距离上次执行是否超过23小时
        last_run = self._last_run_time.get(market_session, datetime.min)
        if (now - last_run) <= timedelta(hours=23):
            return False
        
        return True
    
    def _execute_trend_analysis(self) -> Optional[Dict]:
        """
        执行趋势分析
        
        Returns:
            分析结果字典，包含趋势数据和变化信息
        """
        if not self.user_config.trend.enabled:
            return None
        
        # 获取用户配置的股票列表，如果包含特殊标识则添加热门股票
        symbols = self.user_config.trend.symbols.copy()
        if "TOP_NASDAQ" in symbols:
            symbols.remove("TOP_NASDAQ")
            symbols.extend(get_top_nasdaq_by_volume(20))
        
        logging.info(f"用户 {self.user_config.email} 趋势分析开始，监控股票: {symbols}")
        
        trends: Dict[str, str] = {}
        changes: Dict[str, Tuple[str, str]] = {}
        results: Dict[str, TrendAnalysisResult] = {}
        
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(analyze_trend, sym, user_email=self.user_config.email): sym for sym in symbols}
                for future in as_completed(futures):
                    try:
                        result: TrendAnalysisResult = future.result(timeout=60)
                        symbol = result.symbol
                        
                        if not result.trends or len(result.trends) < 2:
                            continue
                        
                        current_trend = result.trends[-1]
                        trends[symbol] = current_trend
                        results[symbol] = result
                        
                        change = self.detect_trend_change(result.trends)
                        if change:
                            changes[symbol] = change
                            logging.info(f"用户 {self.user_config.email}: {symbol} 趋势变化: {change[0]} → {change[1]}")
                        else:
                            logging.debug(f"用户 {self.user_config.email}: {symbol} 趋势未变: {current_trend}")
                            
                    except Exception as e:
                        logging.error(f"用户 {self.user_config.email}: 分析股票趋势失败: {e}")
                        continue
            
            if trends:
                return {
                    "trends": trends,
                    "changes": changes,
                    "results": results
                }
            else:
                logging.warning(f"用户 {self.user_config.email}: 没有获取到有效的趋势数据")
                return None
                
        except Exception as e:
            logging.error(f"用户 {self.user_config.email}: 趋势分析执行失败: {e}")
            return None
    
    def send_notification(self, analysis_data: Dict) -> bool:
        """
        发送趋势分析邮件给该用户
        
        Args:
            analysis_data: 趋势分析数据
            
        Returns:
            是否发送成功
        """
        if not analysis_data or not analysis_data.get("results"):
            return False
        
        try:
            subject = f"📊 股票趋势日报 - {self.user_config.name or self.user_config.email}"
            html_body = build_trend_email_content(
                analysis_data["results"], 
                analysis_data["changes"]
            )
            system_config = get_system_config()
            
            send_gmail(
                subject=subject,
                html_body=html_body,
                to_emails=[self.user_config.email],
                smtp_server=system_config.smtp_server,
                smtp_port=system_config.smtp_port,
                smtp_user=system_config.sender_email,
                smtp_pass=system_config.sender_password
            )
            
            logging.info(f"已向用户 {self.user_config.email} 发送趋势日报，包含 {len(analysis_data['results'])} 支股票")
            return True
        except Exception as e:
            logging.error(f"向用户 {self.user_config.email} 发送趋势邮件失败: {e}")
            return False
    
    def run_once(self, time_check: bool = True) -> bool:
        """
        执行一次趋势检查和通知
        
        Args:
            time_check: 是否检查执行时间
            
        Returns:
            是否发送了通知
        """
        now = datetime.utcnow()
        
        # 如果不检查时间，直接执行
        if not time_check:
            logging.info(f"用户 {self.user_config.email}: 跳过时间检测，开始趋势分析...")
            analysis_data = self._execute_trend_analysis()
            if analysis_data:
                success = self.send_notification(analysis_data)
                if success:
                    self._last_run_time["pre_market"] = now  # 记录执行时间
                return success
            return False
        
        # 检查是否应该执行盘前分析
        if self._should_run_analysis("pre_market"):
            logging.info(f"用户 {self.user_config.email}: 检测到美股盘前执行时间，开始趋势分析...")
            analysis_data = self._execute_trend_analysis()
            if analysis_data:
                success = self.send_notification(analysis_data)
                if success:
                    self._last_run_time["pre_market"] = now
                return success
        
        # 检查是否应该执行盘后分析
        if self._should_run_analysis("post_market"):
            logging.info(f"用户 {self.user_config.email}: 检测到美股盘后执行时间，开始趋势分析...")
            analysis_data = self._execute_trend_analysis()
            if analysis_data:
                success = self.send_notification(analysis_data)
                if success:
                    self._last_run_time["post_market"] = now
                return success
        
        return False
    
    def get_status(self) -> Dict:
        """
        获取监控器状态信息
        
        Returns:
            状态信息字典
        """
        return {
            "user_email": self.user_config.email,
            "user_name": self.user_config.name,
            "enabled": self.user_config.trend.enabled,
            "pre_market_notification": self.user_config.trend.pre_market_notification,
            "post_market_notification": self.user_config.trend.post_market_notification,
            "monitored_symbols": self.user_config.trend.symbols,
            "last_run_times": {
                session: time.isoformat() if time != datetime.min else None
                for session, time in self._last_run_time.items()
            }
        }