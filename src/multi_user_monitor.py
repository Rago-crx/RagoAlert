"""
多用户监控管理器
负责管理所有用户的监控实例，协调监控任务的执行
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config.config_manager import config_manager, UserConfig
from .monitors.fluctuation_monitor import FluctuationMonitor
from .monitors.trend_monitor import TrendMonitor


class MultiUserMonitorManager:
    """
    多用户监控管理器
    负责创建和管理每个用户的监控实例
    """
    
    def __init__(self):
        self.fluctuation_monitors: Dict[str, FluctuationMonitor] = {}  # email -> FluctuationMonitor
        self.trend_monitors: Dict[str, TrendMonitor] = {}  # email -> TrendMonitor
        self._running = False
        self._fluctuation_thread = None
        self._trend_thread = None
        
        # 监听配置变更
        config_manager.add_config_change_callback(self._on_config_change)
        
        # 初始化所有用户的监控器
        self._initialize_monitors()
    
    def _initialize_monitors(self):
        """初始化所有用户的监控器"""
        all_users = config_manager.get_all_users()
        
        for email, user_config in all_users.items():
            self._create_user_monitors(user_config)
        
        logging.info(f"初始化完成：{len(self.fluctuation_monitors)} 个波动监控器，{len(self.trend_monitors)} 个趋势监控器")
    
    def _create_user_monitors(self, user_config: UserConfig):
        """为指定用户创建监控器"""
        email = user_config.email
        
        # 创建波动监控器
        if user_config.fluctuation.enabled:
            if email not in self.fluctuation_monitors:
                self.fluctuation_monitors[email] = FluctuationMonitor(user_config)
                logging.info(f"创建用户 {email} 的波动监控器")
            else:
                # 更新现有监控器的配置
                self.fluctuation_monitors[email].update_config(user_config)
        else:
            # 如果禁用了波动监控，移除监控器
            if email in self.fluctuation_monitors:
                del self.fluctuation_monitors[email]
                logging.info(f"移除用户 {email} 的波动监控器")
        
        # 创建趋势监控器
        if user_config.trend.enabled:
            if email not in self.trend_monitors:
                self.trend_monitors[email] = TrendMonitor(user_config)
                logging.info(f"创建用户 {email} 的趋势监控器")
            else:
                # 更新现有监控器的配置
                self.trend_monitors[email].update_config(user_config)
        else:
            # 如果禁用了趋势监控，移除监控器
            if email in self.trend_monitors:
                del self.trend_monitors[email]
                logging.info(f"移除用户 {email} 的趋势监控器")
    
    def _on_config_change(self, users: Dict[str, UserConfig]):
        """配置变更回调函数"""
        logging.info("检测到配置变更，更新监控器...")
        
        # 获取当前监控的用户列表
        current_fluctuation_users = set(self.fluctuation_monitors.keys())
        current_trend_users = set(self.trend_monitors.keys())
        new_users = set(users.keys())
        
        # 移除不再存在的用户监控器
        for email in current_fluctuation_users - new_users:
            del self.fluctuation_monitors[email]
            logging.info(f"移除已删除用户 {email} 的波动监控器")
        
        for email in current_trend_users - new_users:
            del self.trend_monitors[email]
            logging.info(f"移除已删除用户 {email} 的趋势监控器")
        
        # 更新或创建用户监控器
        for email, user_config in users.items():
            self._create_user_monitors(user_config)
    
    def _is_us_market_open_or_pre_post(self) -> bool:
        """判断当前时间是否在美股交易时段（包括盘前盘后）内"""
        now_utc = datetime.utcnow()
        is_daylight_saving = 3 <= now_utc.month <= 10
        
        if is_daylight_saving:
            # 夏令时：美东时间 = UTC - 4小时
            # 盘前：UTC 8:00 - 13:30，盘中：UTC 13:30 - 20:00，盘后：UTC 20:00 - 00:00
            market_open_utc = now_utc.replace(hour=13, minute=30, second=0, microsecond=0)
            market_close_utc = now_utc.replace(hour=20, minute=0, second=0, microsecond=0)
            pre_market_open_utc = now_utc.replace(hour=8, minute=0, second=0, microsecond=0)
            post_market_close_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            # 冬令时：美东时间 = UTC - 5小时
            # 盘前：UTC 9:00 - 14:30，盘中：UTC 14:30 - 21:00，盘后：UTC 21:00 - 01:00
            market_open_utc = now_utc.replace(hour=14, minute=30, second=0, microsecond=0)
            market_close_utc = now_utc.replace(hour=21, minute=0, second=0, microsecond=0)
            pre_market_open_utc = now_utc.replace(hour=9, minute=0, second=0, microsecond=0)
            post_market_close_utc = now_utc.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 检查是否在周一到周五
        if now_utc.weekday() >= 5:
            return False
        
        # 检查是否在交易时段内
        return (pre_market_open_utc <= now_utc < market_open_utc) or \
               (market_open_utc <= now_utc < market_close_utc) or \
               (market_close_utc <= now_utc < post_market_close_utc)
    
    def _run_fluctuation_monitoring(self):
        """波动监控主循环"""
        logging.info("启动波动监控线程")
        
        while self._running:
            try:
                if not self._is_us_market_open_or_pre_post():
                    logging.debug("当前不在美股交易时段，波动监控暂停")
                    time.sleep(60)
                    continue
                
                if not self.fluctuation_monitors:
                    logging.debug("没有启用波动监控的用户")
                    time.sleep(60)
                    continue
                
                # 使用线程池并发执行所有用户的波动监控
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for email, monitor in self.fluctuation_monitors.items():
                        future = executor.submit(monitor.run_once)
                        futures.append((email, future))
                    
                    # 收集结果
                    notification_count = 0
                    for email, future in futures:
                        try:
                            if future.result(timeout=30):  # 30秒超时
                                notification_count += 1
                        except Exception as e:
                            logging.error(f"用户 {email} 波动监控执行失败: {e}")
                    
                    if notification_count > 0:
                        logging.info(f"本轮波动监控发送了 {notification_count} 个通知")
                
                time.sleep(60)  # 每分钟执行一次
                
            except Exception as e:
                logging.error(f"波动监控线程异常: {e}")
                time.sleep(60)
    
    def _run_trend_monitoring(self):
        """趋势监控主循环"""
        logging.info("启动趋势监控线程")
        
        while self._running:
            try:
                if not self.trend_monitors:
                    logging.debug("没有启用趋势监控的用户")
                    time.sleep(1800)  # 30分钟后再检查
                    continue
                
                # 使用线程池并发执行所有用户的趋势监控
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = []
                    for email, monitor in self.trend_monitors.items():
                        future = executor.submit(monitor.run_once)
                        futures.append((email, future))
                    
                    # 收集结果
                    notification_count = 0
                    for email, future in futures:
                        try:
                            if future.result(timeout=300):  # 5分钟超时
                                notification_count += 1
                        except Exception as e:
                            logging.error(f"用户 {email} 趋势监控执行失败: {e}")
                    
                    if notification_count > 0:
                        logging.info(f"本轮趋势监控发送了 {notification_count} 个通知")
                
                time.sleep(1800)  # 每30分钟检查一次
                
            except Exception as e:
                logging.error(f"趋势监控线程异常: {e}")
                time.sleep(1800)
    
    def start(self):
        """启动多用户监控"""
        if self._running:
            logging.warning("多用户监控已在运行")
            return
        
        self._running = True
        
        # 启动波动监控线程
        self._fluctuation_thread = threading.Thread(
            target=self._run_fluctuation_monitoring,
            name="FluctuationMonitorThread",
            daemon=True
        )
        self._fluctuation_thread.start()
        
        # 启动趋势监控线程
        self._trend_thread = threading.Thread(
            target=self._run_trend_monitoring,
            name="TrendMonitorThread",
            daemon=True
        )
        self._trend_thread.start()
        
        logging.info("多用户监控已启动")
    
    def stop(self):
        """停止多用户监控"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待线程结束
        if self._fluctuation_thread and self._fluctuation_thread.is_alive():
            self._fluctuation_thread.join(timeout=5)
        
        if self._trend_thread and self._trend_thread.is_alive():
            self._trend_thread.join(timeout=5)
        
        logging.info("多用户监控已停止")
    
    def get_status(self) -> Dict:
        """获取监控状态"""
        return {
            "running": self._running,
            "fluctuation_monitors": len(self.fluctuation_monitors),
            "trend_monitors": len(self.trend_monitors),
            "fluctuation_users": list(self.fluctuation_monitors.keys()),
            "trend_users": list(self.trend_monitors.keys()),
            "fluctuation_thread_alive": self._fluctuation_thread.is_alive() if self._fluctuation_thread else False,
            "trend_thread_alive": self._trend_thread.is_alive() if self._trend_thread else False
        }


# 全局监控管理器实例
monitor_manager = MultiUserMonitorManager()