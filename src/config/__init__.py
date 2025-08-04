"""
配置管理模块
"""

from .config_manager import (
    config_manager,
    UserConfig,
    UserFluctuationConfig,
    UserTrendConfig,
    TrendAnalysisConfig,
    SystemConfig,
    get_system_config,
    get_trend_analysis_config
)

__all__ = [
    'config_manager',
    'UserConfig',
    'UserFluctuationConfig', 
    'UserTrendConfig',
    'TrendAnalysisConfig',
    'SystemConfig',
    'get_system_config',
    'get_trend_analysis_config'
]