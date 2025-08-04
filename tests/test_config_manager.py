"""
配置管理器测试
"""

import unittest
import tempfile
import os
import yaml
from unittest.mock import patch

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.config.config_manager import MultiUserConfigManager, UserConfig, TrendAnalysisConfig


class TestConfigManager(unittest.TestCase):
    
    def setUp(self):
        """测试前设置"""
        self.test_dir = tempfile.mkdtemp()
        self.users_config_file = os.path.join(self.test_dir, "test_users_config.yaml")
        self.system_config_file = os.path.join(self.test_dir, "test_system_config.yaml")
        
        # 创建测试配置管理器
        self.config_manager = MultiUserConfigManager(
            config_file=self.users_config_file,
            system_config_file=self.system_config_file
        )
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_create_default_configs(self):
        """测试创建默认配置"""
        # 配置文件应该被创建
        self.assertTrue(os.path.exists(self.users_config_file))
        self.assertTrue(os.path.exists(self.system_config_file))
        
        # 系统配置应该有默认值
        self.assertEqual(self.config_manager.system_config.web_port, 8080)
        self.assertEqual(self.config_manager.system_config.smtp_server, "smtp.gmail.com")
    
    def test_create_user(self):
        """测试创建用户"""
        email = "test@example.com"
        success = self.config_manager.create_or_update_user(
            email=email,
            name="Test User",
            fluctuation_threshold_percent=2.5,
            fluctuation_symbols=["AAPL", "TSLA"],
            trend_symbols=["NASDAQ_CORE"]
        )
        
        self.assertTrue(success)
        
        # 验证用户配置
        user_config = self.config_manager.get_user_config(email)
        self.assertIsNotNone(user_config)
        self.assertEqual(user_config.name, "Test User")
        self.assertEqual(user_config.fluctuation.threshold_percent, 2.5)
        
        # 验证股票池展开
        self.assertIn("AAPL", user_config.trend.symbols)
        self.assertIn("MSFT", user_config.trend.symbols)  # 来自NASDAQ_CORE
    
    def test_stock_pool_expansion(self):
        """测试股票池展开功能"""
        # 先设置测试用的股票池
        self.config_manager.system_config.stock_pools = {
            "ai_chips": ['NVDA', 'AMD', 'ASML', 'ARM', 'INTC'],
            "china_tech": ['BIDU', 'BABA', 'JD', 'PDD']
        }
        
        symbols = ["AAPL", "ai_chips", "TSLA"]
        expanded = self.config_manager._expand_stock_symbols(symbols)
        
        # 应该包含直接股票
        self.assertIn("AAPL", expanded)
        self.assertIn("TSLA", expanded)
        
        # 应该包含ai_chips池中的股票
        self.assertIn("NVDA", expanded)
        self.assertIn("AMD", expanded)
    
    def test_at_symbol_reference(self):
        """测试@符号股票池引用功能"""
        # 先设置测试用的股票池
        self.config_manager.system_config.stock_pools = {
            "ai_chips": ['NVDA', 'AMD', 'ASML', 'ARM', 'INTC'],
            "china_tech": ['BIDU', 'BABA', 'JD', 'PDD']
        }
        
        # 测试单个@引用
        symbols = ["@ai_chips"]
        expanded = self.config_manager._expand_stock_symbols(symbols)
        self.assertIn("NVDA", expanded)
        self.assertIn("AMD", expanded)
        self.assertIn("ASML", expanded)
        
        # 测试@引用 + 直接股票
        symbols = ["@china_tech", "TSLA", "NVDA"]
        expanded = self.config_manager._expand_stock_symbols(symbols)
        self.assertIn("BIDU", expanded)  # 来自@china_tech
        self.assertIn("BABA", expanded)  # 来自@china_tech
        self.assertIn("TSLA", expanded)  # 直接股票
        self.assertIn("NVDA", expanded)  # 直接股票
        
        # 测试多个@引用
        symbols = ["@china_tech", "@ai_chips"]
        expanded = self.config_manager._expand_stock_symbols(symbols)
        self.assertIn("BIDU", expanded)  # 来自@china_tech
        self.assertIn("NVDA", expanded)  # 来自@ai_chips
        
        # 测试不存在的@引用（应该警告但不崩溃）
        symbols = ["@non_existent", "AAPL"]
        expanded = self.config_manager._expand_stock_symbols(symbols)
        self.assertIn("AAPL", expanded)
        self.assertNotIn("@non_existent", expanded)
        
        # 测试字符串形式的单个@引用
        symbol_str = "@china_tech"
        expanded = self.config_manager._expand_stock_symbols(symbol_str)
        self.assertIn("BIDU", expanded)
        self.assertIn("BABA", expanded)
    
    def test_trend_analysis_config(self):
        """测试趋势分析配置"""
        email = "trader@example.com"
        
        # 创建有自定义趋势配置的用户
        user_config = UserConfig(email=email)
        user_config.trend.analysis_config = TrendAnalysisConfig(
            up_trend_threshold=2,
            down_trend_threshold=2,
            buy_signal_threshold=0.7
        )
        self.config_manager.users[email] = user_config
        
        # 获取用户的趋势配置
        trend_config = self.config_manager.get_trend_analysis_config(email)
        self.assertEqual(trend_config.up_trend_threshold, 2)
        self.assertEqual(trend_config.buy_signal_threshold, 0.7)
        
        # 测试默认配置
        default_config = self.config_manager.get_trend_analysis_config("nonexistent@example.com")
        self.assertEqual(default_config.up_trend_threshold, 3)  # 系统默认值
    
    def test_config_persistence(self):
        """测试配置持久化"""
        email = "persistent@example.com"
        
        # 创建用户
        self.config_manager.create_or_update_user(
            email=email,
            name="Persistent User"
        )
        
        # 重新创建配置管理器（模拟重启）
        new_manager = MultiUserConfigManager(
            config_file=self.users_config_file,
            system_config_file=self.system_config_file
        )
        
        # 验证配置被正确加载
        user_config = new_manager.get_user_config(email)
        self.assertIsNotNone(user_config)
        self.assertEqual(user_config.name, "Persistent User")


if __name__ == "__main__":
    unittest.main()