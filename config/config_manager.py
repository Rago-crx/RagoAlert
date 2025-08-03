"""
多用户动态配置管理系统 - YAML版本
支持按邮箱地址分离用户配置，每个用户独立的监控设置
"""

import yaml
import threading
import os
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

@dataclass
class TrendAnalysisConfig:
    """趋势分析配置"""
    # 趋势判断阈值
    up_trend_threshold: int = 3
    down_trend_threshold: int = 3
    
    # 信号权重配置
    signal_weights: Dict[str, float] = None
    
    # 信号阈值配置
    buy_signal_threshold: float = 0.8
    sell_signal_threshold: float = 0.8
    
    # 技术指标参数
    ema_short_period: int = 7
    ema_long_period: int = 20
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    adx_period: int = 14
    adx_threshold: float = 25.0
    bb_period: int = 20
    bb_std_dev: float = 2.0
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    def __post_init__(self):
        if self.signal_weights is None:
            self.signal_weights = {
                'ema_cross': 0.3,
                'macd_cross': 0.2,
                'adx_strength': 0.2,
                'bb_position': 0.15,
                'rsi_level': 0.15
            }

@dataclass
class UserFluctuationConfig:
    """用户波动监控配置"""
    threshold_percent: float = 3.0  # 波动阈值百分比
    symbols: List[str] = None  # 监控的股票代码列表
    notification_interval_minutes: int = 5  # 通知间隔（分钟）
    enabled: bool = True  # 是否启用波动监控
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]

@dataclass
class UserTrendConfig:
    """用户趋势监控配置"""
    enabled: bool = True  # 是否启用趋势监控
    symbols: List[str] = None  # 监控的股票代码列表
    pre_market_notification: bool = True  # 盘前通知
    post_market_notification: bool = True  # 盘后通知
    # 用户自定义趋势分析配置（可选）
    analysis_config: Optional[TrendAnalysisConfig] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]

@dataclass 
class UserConfig:
    """单个用户配置"""
    email: str  # 用户邮箱（唯一标识）
    name: str = ""  # 用户名称
    fluctuation: UserFluctuationConfig = None
    trend: UserTrendConfig = None
    created_at: str = ""  # 创建时间
    updated_at: str = ""  # 更新时间
    
    def __post_init__(self):
        if self.fluctuation is None:
            self.fluctuation = UserFluctuationConfig()
        if self.trend is None:
            self.trend = UserTrendConfig()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

@dataclass
class SystemConfig:
    """系统配置"""
    # SMTP配置
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    sender_email: str = ""  # 系统发送邮箱
    sender_password: str = ""  # 系统发送邮箱密码
    sender_name: str = "RagoAlert"
    
    # Web配置
    web_port: int = 8080
    web_host: str = "0.0.0.0"
    
    # 系统配置
    log_level: str = "INFO"
    timezone: str = "UTC"
    
    # 全局趋势分析配置
    trend_analysis: TrendAnalysisConfig = None
    
    # 预定义股票池
    stock_pools: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.trend_analysis is None:
            self.trend_analysis = TrendAnalysisConfig()
        if self.stock_pools is None:
            self.stock_pools = {}
    

class MultiUserConfigManager:
    """多用户配置管理器 - YAML版本"""
    
    def __init__(self, config_file: str = None, system_config_file: str = None):
        # 从环境变量读取配置文件路径，如果没有则使用默认值
        self.config_file = config_file or os.getenv('RAGOALERT_CONFIG', 'users_config.yaml')
        self.system_config_file = system_config_file or os.getenv('RAGOALERT_SYSTEM_CONFIG', 'system_config.yaml')
        self.users: Dict[str, UserConfig] = {}  # email -> UserConfig
        self.system_config = SystemConfig()
        self._lock = threading.RLock()
        self._callbacks = []  # 配置变更回调函数列表
        
        # 加载配置
        self.load_all_configs()
    
    def _expand_stock_symbols(self, symbols: List[str]) -> List[str]:
        """展开股票池引用，将股票池名称替换为实际股票列表"""
        if isinstance(symbols, str):
            # 如果是单个字符串（@引用），转换为列表
            symbols = [symbols]
        
        expanded = []
        for symbol in symbols:
            if symbol.startswith('@'):
                # 处理@引用，如 "@china_tech"
                pool_name = symbol[1:]  # 移除@符号
                if pool_name in self.system_config.stock_pools:
                    expanded.extend(self.system_config.stock_pools[pool_name])
                else:
                    logging.warning(f"股票池引用不存在: {pool_name}")
            elif symbol in self.system_config.stock_pools:
                # 如果是股票池名称，展开为具体股票
                expanded.extend(self.system_config.stock_pools[symbol])
            else:
                # 否则直接添加
                expanded.append(symbol)
        # 去重并保持顺序
        seen = set()
        result = []
        for s in expanded:
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result
    
    def load_all_configs(self):
        """加载所有配置"""
        self.load_system_config()
        self.load_users_config()
    
    def load_users_config(self) -> bool:
        """加载用户配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                self.users = {}
                for email, user_data in data.items():
                    if email.startswith('_') or email in ['configuration_guide', 'deployment_steps', 'security_notes']:
                        continue  # 跳过注释和说明
                    
                    # 解析波动配置
                    fluctuation_data = user_data.get('fluctuation', {})
                    fluctuation_config = UserFluctuationConfig(
                        threshold_percent=fluctuation_data.get('threshold_percent', 3.0),
                        symbols=fluctuation_data.get('symbols', []),
                        notification_interval_minutes=fluctuation_data.get('notification_interval_minutes', 5),
                        enabled=fluctuation_data.get('enabled', True)
                    )
                    
                    # 解析趋势配置
                    trend_data = user_data.get('trend', {})
                    
                    # 解析用户自定义趋势分析配置
                    analysis_config = None
                    if 'analysis_config' in trend_data:
                        ac_data = trend_data['analysis_config']
                        analysis_config = TrendAnalysisConfig(
                            up_trend_threshold=ac_data.get('thresholds', {}).get('up_trend', 3),
                            down_trend_threshold=ac_data.get('thresholds', {}).get('down_trend', 3),
                            signal_weights=ac_data.get('signal_weights', None),
                            buy_signal_threshold=ac_data.get('signal_thresholds', {}).get('buy_signal', 0.8),
                            sell_signal_threshold=ac_data.get('signal_thresholds', {}).get('sell_signal', 0.8)
                        )
                    
                    trend_config = UserTrendConfig(
                        enabled=trend_data.get('enabled', True),
                        symbols=trend_data.get('symbols', []),
                        pre_market_notification=trend_data.get('notifications', {}).get('pre_market', True),
                        post_market_notification=trend_data.get('notifications', {}).get('post_market', True),
                        analysis_config=analysis_config
                    )
                    
                    # 展开股票池引用
                    fluctuation_config.symbols = self._expand_stock_symbols(fluctuation_config.symbols)
                    trend_config.symbols = self._expand_stock_symbols(trend_config.symbols)
                    
                    self.users[email] = UserConfig(
                        email=email,
                        name=user_data.get('profile', {}).get('name', ''),
                        fluctuation=fluctuation_config,
                        trend=trend_config,
                        created_at=user_data.get('profile', {}).get('created_at', ''),
                        updated_at=user_data.get('profile', {}).get('updated_at', '')
                    )
                
                logging.info(f"用户配置加载成功: {len(self.users)} 个用户")
                return True
            else:
                logging.info("用户配置文件不存在，创建空配置")
                self.save_users_config()
                return True
        except Exception as e:
            logging.error(f"加载用户配置失败: {e}")
            return False
    
    def load_system_config(self) -> bool:
        """加载系统配置"""
        try:
            if os.path.exists(self.system_config_file):
                with open(self.system_config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # 解析SMTP配置
                smtp_data = data.get('smtp', {})
                
                # 解析Web配置
                web_data = data.get('web', {})
                
                # 解析系统配置
                system_data = data.get('system', {})
                
                # 解析趋势分析配置
                trend_analysis_data = data.get('trend_analysis', {})
                thresholds = trend_analysis_data.get('thresholds', {})
                signal_weights = trend_analysis_data.get('signal_weights', {})
                signal_thresholds = trend_analysis_data.get('signal_thresholds', {})
                indicators = trend_analysis_data.get('indicators', {})
                
                trend_analysis = TrendAnalysisConfig(
                    up_trend_threshold=thresholds.get('up_trend', 3),
                    down_trend_threshold=thresholds.get('down_trend', 3),
                    signal_weights=signal_weights if signal_weights else None,
                    buy_signal_threshold=signal_thresholds.get('buy_signal', 0.8),
                    sell_signal_threshold=signal_thresholds.get('sell_signal', 0.8),
                    ema_short_period=indicators.get('ema', {}).get('short_period', 7),
                    ema_long_period=indicators.get('ema', {}).get('long_period', 20),
                    macd_fast_period=indicators.get('macd', {}).get('fast_period', 12),
                    macd_slow_period=indicators.get('macd', {}).get('slow_period', 26),
                    macd_signal_period=indicators.get('macd', {}).get('signal_period', 9),
                    adx_period=indicators.get('adx', {}).get('period', 14),
                    adx_threshold=indicators.get('adx', {}).get('threshold', 25.0),
                    bb_period=indicators.get('bollinger_bands', {}).get('period', 20),
                    bb_std_dev=indicators.get('bollinger_bands', {}).get('std_dev', 2.0),
                    rsi_period=indicators.get('rsi', {}).get('period', 14),
                    rsi_overbought=indicators.get('rsi', {}).get('overbought', 70.0),
                    rsi_oversold=indicators.get('rsi', {}).get('oversold', 30.0)
                )
                
                self.system_config = SystemConfig(
                    smtp_server=smtp_data.get('server', 'smtp.gmail.com'),
                    smtp_port=smtp_data.get('port', 465),
                    sender_email=smtp_data.get('user', ''),
                    sender_password=smtp_data.get('password', ''),
                    sender_name=smtp_data.get('sender_name', 'RagoAlert'),
                    web_port=web_data.get('port', 8080),
                    web_host=web_data.get('host', '0.0.0.0'),
                    log_level=system_data.get('log_level', 'INFO'),
                    timezone=system_data.get('timezone', 'UTC'),
                    trend_analysis=trend_analysis,
                    stock_pools=data.get('stock_pools', {})
                )
                
                logging.info("系统配置加载成功")
                return True
            else:
                logging.info("系统配置文件不存在，创建默认配置")
                self.save_system_config()
                return True
        except Exception as e:
            logging.error(f"加载系统配置失败: {e}")
            return False
    
    def save_users_config(self) -> bool:
        """保存用户配置"""
        try:
            with self._lock:
                data = {}
                for email, user_config in self.users.items():
                    # 构建趋势配置
                    trend_data = {
                        'enabled': user_config.trend.enabled,
                        'symbols': user_config.trend.symbols,
                        'notifications': {
                            'pre_market': user_config.trend.pre_market_notification,
                            'post_market': user_config.trend.post_market_notification
                        }
                    }
                    
                    # 如果有自定义趋势分析配置，添加到配置中
                    if user_config.trend.analysis_config:
                        ac = user_config.trend.analysis_config
                        trend_data['analysis_config'] = {
                            'thresholds': {
                                'up_trend': ac.up_trend_threshold,
                                'down_trend': ac.down_trend_threshold
                            },
                            'signal_weights': ac.signal_weights,
                            'signal_thresholds': {
                                'buy_signal': ac.buy_signal_threshold,
                                'sell_signal': ac.sell_signal_threshold
                            }
                        }
                    
                    data[email] = {
                        'profile': {
                            'name': user_config.name,
                            'created_at': user_config.created_at,
                            'updated_at': user_config.updated_at
                        },
                        'fluctuation': {
                            'enabled': user_config.fluctuation.enabled,
                            'threshold_percent': user_config.fluctuation.threshold_percent,
                            'symbols': user_config.fluctuation.symbols,
                            'notification_interval_minutes': user_config.fluctuation.notification_interval_minutes
                        },
                        'trend': trend_data
                    }
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
                
                logging.info("用户配置保存成功")
                self._notify_config_change()
                return True
        except Exception as e:
            logging.error(f"保存用户配置失败: {e}")
            return False
    
    def save_system_config(self) -> bool:
        """保存系统配置"""
        try:
            with self._lock:
                data = {
                    'smtp': {
                        'server': self.system_config.smtp_server,
                        'port': self.system_config.smtp_port,
                        'user': self.system_config.sender_email,
                        'password': self.system_config.sender_password,
                        'sender_name': self.system_config.sender_name
                    },
                    'web': {
                        'port': self.system_config.web_port,
                        'host': self.system_config.web_host
                    },
                    'system': {
                        'log_level': self.system_config.log_level,
                        'timezone': self.system_config.timezone
                    },
                    'trend_analysis': {
                        'thresholds': {
                            'up_trend': self.system_config.trend_analysis.up_trend_threshold,
                            'down_trend': self.system_config.trend_analysis.down_trend_threshold
                        },
                        'signal_weights': self.system_config.trend_analysis.signal_weights,
                        'signal_thresholds': {
                            'buy_signal': self.system_config.trend_analysis.buy_signal_threshold,
                            'sell_signal': self.system_config.trend_analysis.sell_signal_threshold
                        },
                        'indicators': {
                            'ema': {
                                'short_period': self.system_config.trend_analysis.ema_short_period,
                                'long_period': self.system_config.trend_analysis.ema_long_period
                            },
                            'macd': {
                                'fast_period': self.system_config.trend_analysis.macd_fast_period,
                                'slow_period': self.system_config.trend_analysis.macd_slow_period,
                                'signal_period': self.system_config.trend_analysis.macd_signal_period
                            },
                            'adx': {
                                'period': self.system_config.trend_analysis.adx_period,
                                'threshold': self.system_config.trend_analysis.adx_threshold
                            },
                            'bollinger_bands': {
                                'period': self.system_config.trend_analysis.bb_period,
                                'std_dev': self.system_config.trend_analysis.bb_std_dev
                            },
                            'rsi': {
                                'period': self.system_config.trend_analysis.rsi_period,
                                'overbought': self.system_config.trend_analysis.rsi_overbought,
                                'oversold': self.system_config.trend_analysis.rsi_oversold
                            }
                        }
                    },
                    'stock_pools': self.system_config.stock_pools
                }
                
                with open(self.system_config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
                
                logging.info("系统配置保存成功")
                return True
        except Exception as e:
            logging.error(f"保存系统配置失败: {e}")
            return False
    
    def get_user_config(self, email: str) -> Optional[UserConfig]:
        """获取指定用户配置"""
        with self._lock:
            return self.users.get(email)
    
    def get_trend_analysis_config(self, email: str) -> TrendAnalysisConfig:
        """获取用户的趋势分析配置，如果用户没有自定义则使用系统默认"""
        user_config = self.get_user_config(email)
        if user_config and user_config.trend.analysis_config:
            return user_config.trend.analysis_config
        return self.system_config.trend_analysis
    
    def create_or_update_user(self, email: str, **kwargs) -> bool:
        """创建或更新用户配置"""
        try:
            with self._lock:
                if email in self.users:
                    user_config = self.users[email]
                    user_config.updated_at = datetime.now().isoformat()
                else:
                    user_config = UserConfig(email=email)
                    self.users[email] = user_config
                
                # 更新用户属性
                for key, value in kwargs.items():
                    if key == 'name':
                        user_config.name = value
                    elif key.startswith('fluctuation_'):
                        attr_name = key.replace('fluctuation_', '')
                        if hasattr(user_config.fluctuation, attr_name):
                            setattr(user_config.fluctuation, attr_name, value)
                    elif key.startswith('trend_'):
                        attr_name = key.replace('trend_', '')
                        if hasattr(user_config.trend, attr_name):
                            setattr(user_config.trend, attr_name, value)
                
                # 展开股票池引用
                user_config.fluctuation.symbols = self._expand_stock_symbols(user_config.fluctuation.symbols)
                user_config.trend.symbols = self._expand_stock_symbols(user_config.trend.symbols)
                
                user_config.updated_at = datetime.now().isoformat()
                logging.info(f"用户配置更新: {email}")
                
                return self.save_users_config()
        except Exception as e:
            logging.error(f"更新用户配置失败: {e}")
            return False
    
    def delete_user(self, email: str) -> bool:
        """删除用户配置"""
        try:
            with self._lock:
                if email in self.users:
                    del self.users[email]
                    logging.info(f"用户配置删除: {email}")
                    return self.save_users_config()
                return False
        except Exception as e:
            logging.error(f"删除用户配置失败: {e}")
            return False
    
    def get_all_users(self) -> Dict[str, UserConfig]:
        """获取所有用户配置"""
        with self._lock:
            return self.users.copy()
    
    def get_fluctuation_enabled_users(self) -> Dict[str, UserConfig]:
        """获取启用波动监控的用户"""
        with self._lock:
            return {email: user for email, user in self.users.items() 
                   if user.fluctuation.enabled}
    
    def get_trend_enabled_users(self) -> Dict[str, UserConfig]:
        """获取启用趋势监控的用户"""
        with self._lock:
            return {email: user for email, user in self.users.items() 
                   if user.trend.enabled}
    
    def get_all_monitored_symbols(self) -> Set[str]:
        """获取所有用户监控的股票代码（去重）"""
        symbols = set()
        with self._lock:
            for user in self.users.values():
                if user.fluctuation.enabled:
                    symbols.update(user.fluctuation.symbols)
                if user.trend.enabled:
                    # 过滤掉特殊标识符
                    user_symbols = [s for s in user.trend.symbols if not s.startswith('TOP_')]
                    symbols.update(user_symbols)
        return symbols
    
    def get_users_for_symbol(self, symbol: str, monitor_type: str = 'fluctuation') -> List[UserConfig]:
        """获取监控指定股票的用户列表"""
        users = []
        with self._lock:
            for user in self.users.values():
                if monitor_type == 'fluctuation' and user.fluctuation.enabled:
                    if symbol in user.fluctuation.symbols:
                        users.append(user)
                elif monitor_type == 'trend' and user.trend.enabled:
                    if symbol in user.trend.symbols:
                        users.append(user)
        return users
    
    def update_system_config(self, **kwargs) -> bool:
        """更新系统配置"""
        try:
            with self._lock:
                for key, value in kwargs.items():
                    if hasattr(self.system_config, key):
                        setattr(self.system_config, key, value)
                        logging.info(f"更新系统配置: {key} = {value}")
                
                return self.save_system_config()
        except Exception as e:
            logging.error(f"更新系统配置失败: {e}")
            return False
    
    def add_config_change_callback(self, callback):
        """添加配置变更回调函数"""
        self._callbacks.append(callback)
    
    def _notify_config_change(self):
        """通知配置变更"""
        for callback in self._callbacks:
            try:
                callback(self.users)
            except Exception as e:
                logging.error(f"配置变更回调执行失败: {e}")
    
    def reload_all_configs(self) -> bool:
        """重新加载所有配置"""
        return self.load_all_configs()

# 全局多用户配置管理器实例
config_manager = MultiUserConfigManager()

# 便捷函数
def get_all_users() -> Dict[str, UserConfig]:
    """获取所有用户配置"""
    return config_manager.get_all_users()

def get_fluctuation_enabled_users() -> Dict[str, UserConfig]:
    """获取启用波动监控的用户"""
    return config_manager.get_fluctuation_enabled_users()

def get_trend_enabled_users() -> Dict[str, UserConfig]:
    """获取启用趋势监控的用户"""
    return config_manager.get_trend_enabled_users()

def get_all_monitored_symbols() -> Set[str]:
    """获取所有监控的股票代码"""
    return config_manager.get_all_monitored_symbols()

def get_users_for_symbol(symbol: str, monitor_type: str = 'fluctuation') -> List[UserConfig]:
    """获取监控指定股票的用户"""
    return config_manager.get_users_for_symbol(symbol, monitor_type)

def get_system_config() -> SystemConfig:
    """获取系统配置"""
    return config_manager.system_config

def get_trend_analysis_config(email: str = None) -> TrendAnalysisConfig:
    """获取趋势分析配置"""
    if email:
        return config_manager.get_trend_analysis_config(email)
    return config_manager.system_config.trend_analysis