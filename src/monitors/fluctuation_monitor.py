"""
单用户波动监控器
重构为只处理单个用户的波动监控逻辑
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from collections import deque

from src.config.config_manager import UserConfig, get_system_config
from src.data.yahoo import get_current_price
from src.notifiers.email import send_gmail, build_fluctuation_email_content
from src.indicators.fluctuation import FluctuationAnalyzer, FluctuationAnalysisResult


class FluctuationMonitor:
    """
    单用户波动监控器
    负责监控单个用户配置的股票价格波动
    """
    
    def __init__(self, user_config: UserConfig):
        """
        初始化波动监控器
        
        Args:
            user_config: 用户配置对象
        """
        self.user_config = user_config
        # 存储该用户监控股票的历史价格
        self._price_history: Dict[str, deque] = {}
        # 记录该用户每个股票的上次通知时间
        self._last_notification_time: Dict[str, datetime] = {}
        
        # 初始化价格历史
        for symbol in self.user_config.fluctuation.symbols:
            self._price_history[symbol] = deque(maxlen=60)  # 存储最近60分钟的价格
            self._last_notification_time[symbol] = datetime.min
        
        logging.info(f"初始化用户 {self.user_config.email} 的波动监控器，监控股票: {self.user_config.fluctuation.symbols}")
    
    def update_config(self, new_user_config: UserConfig):
        """
        更新用户配置
        
        Args:
            new_user_config: 新的用户配置
        """
        old_symbols = set(self.user_config.fluctuation.symbols)
        new_symbols = set(new_user_config.fluctuation.symbols)
        
        # 移除不再监控的股票历史数据
        for symbol in old_symbols - new_symbols:
            if symbol in self._price_history:
                del self._price_history[symbol]
            if symbol in self._last_notification_time:
                del self._last_notification_time[symbol]
        
        # 为新增的股票初始化历史数据
        for symbol in new_symbols - old_symbols:
            self._price_history[symbol] = deque(maxlen=60)
            self._last_notification_time[symbol] = datetime.min
        
        self.user_config = new_user_config
        logging.info(f"更新用户 {self.user_config.email} 的波动监控配置")
    
    def check_fluctuations(self) -> List[FluctuationAnalysisResult]:
        """
        检查该用户监控股票的波动情况
        返回触发通知条件的波动分析结果列表
        """
        if not self.user_config.fluctuation.enabled:
            return []
            
        fluctuation_results = []
        now = datetime.now()
        
        for symbol in self.user_config.fluctuation.symbols:
            try:
                current_price = get_current_price(symbol)
                if current_price == 0.0:
                    logging.warning(f"用户 {self.user_config.email}: 无法获取 {symbol} 的实时价格，跳过。")
                    continue

                # 更新价格历史
                self._price_history[symbol].append((now, current_price))

                # 波动分析
                analysis_result = FluctuationAnalyzer.analyze_fluctuation(
                    symbol=symbol,
                    price_history=self._price_history[symbol],
                    current_price=current_price,
                    time_window_minutes=1
                )

                if analysis_result is None:
                    continue

                # 检查是否达到该用户的波动阈值
                if abs(analysis_result.percentage_change) >= self.user_config.fluctuation.threshold_percent:
                    # 检查通知间隔
                    last_notif_time = self._last_notification_time.get(symbol, datetime.min)
                    if now - last_notif_time >= timedelta(minutes=self.user_config.fluctuation.notification_interval_minutes):
                        fluctuation_results.append(analysis_result)
                        self._last_notification_time[symbol] = now
                        logging.info(f"用户 {self.user_config.email}: {symbol} 波动 {analysis_result.percentage_change:.2f}% 触发通知")
                    else:
                        remaining_time = self.user_config.fluctuation.notification_interval_minutes - (now - last_notif_time).total_seconds() / 60
                        logging.debug(f"用户 {self.user_config.email}: {symbol} 波动达到阈值但在通知间隔内，还需等待 {remaining_time:.1f} 分钟")
                else:
                    logging.debug(f"用户 {self.user_config.email}: {symbol} 波动 {analysis_result.percentage_change:.2f}% 未达到阈值 {self.user_config.fluctuation.threshold_percent}%")
            
            except Exception as e:
                logging.error(f"用户 {self.user_config.email}: 检查 {symbol} 波动时出错: {e}")
                continue
        
        return fluctuation_results
    
    def send_notification(self, fluctuation_results: List[FluctuationAnalysisResult]) -> bool:
        """
        发送波动通知邮件给该用户
        
        Args:
            fluctuation_results: 波动分析结果列表
            
        Returns:
            是否发送成功
        """
        if not fluctuation_results:
            return False
            
        try:
            subject = f"🚨 股票波动提醒 - {self.user_config.name or self.user_config.email}"
            html_body = build_fluctuation_email_content(fluctuation_results)
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
            
            logging.info(f"已向用户 {self.user_config.email} 发送包含 {len(fluctuation_results)} 支股票波动的邮件")
            return True
        except Exception as e:
            logging.error(f"向用户 {self.user_config.email} 发送邮件失败: {e}")
            return False
    
    def run_once(self) -> bool:
        """
        执行一次波动检查和通知
        
        Returns:
            是否发送了通知
        """
        fluctuation_results = self.check_fluctuations()
        if fluctuation_results:
            return self.send_notification(fluctuation_results)
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
            "enabled": self.user_config.fluctuation.enabled,
            "threshold_percent": self.user_config.fluctuation.threshold_percent,
            "notification_interval_minutes": self.user_config.fluctuation.notification_interval_minutes,
            "monitored_symbols": self.user_config.fluctuation.symbols,
            "price_history_count": {symbol: len(history) for symbol, history in self._price_history.items()},
            "last_notification_times": {
                symbol: time.isoformat() if time != datetime.min else None 
                for symbol, time in self._last_notification_time.items()
            }
        }