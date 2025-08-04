"""
趋势分析测试
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.indicators.trend import analyze_trend, TrendAnalysisResult
from src.config.config_manager import TrendAnalysisConfig


class TestTrendAnalysis(unittest.TestCase):
    
    def setUp(self):
        """测试前设置"""
        self.test_config = TrendAnalysisConfig(
            up_trend_threshold=2,
            down_trend_threshold=2,
            ema_short_period=5,
            ema_long_period=10,
            buy_signal_threshold=0.6,
            sell_signal_threshold=0.6
        )
    
    def create_test_data(self, trend_type="up"):
        """创建测试用的股价数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        if trend_type == "up":
            # 上涨趋势数据
            prices = np.linspace(100, 150, 100) + np.random.normal(0, 2, 100)
        elif trend_type == "down":
            # 下跌趋势数据
            prices = np.linspace(150, 100, 100) + np.random.normal(0, 2, 100)
        else:
            # 横盘数据
            prices = 125 + np.random.normal(0, 3, 100)
        
        # 确保价格为正数
        prices = np.maximum(prices, 50)
        
        df = pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)
        
        return df
    
    @patch('src.indicators.trend.yf.Ticker')
    @patch('src.indicators.trend.get_trend_analysis_config')
    def test_analyze_trend_up(self, mock_get_config, mock_ticker):
        """测试上涨趋势分析"""
        mock_get_config.return_value = self.test_config
        
        # 创建模拟ticker对象
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.create_test_data("up")
        mock_ticker.return_value = mock_ticker_instance
        
        # 执行趋势分析
        result = analyze_trend("AAPL", user_email="test@example.com")
        
        # 验证结果
        self.assertIsInstance(result, TrendAnalysisResult)
        self.assertEqual(result.symbol, "AAPL")
        self.assertIsNotNone(result.trends)
        self.assertGreater(len(result.trends), 0)
        
        # 检查是否有上涨趋势
        up_count = result.trends.count("up")
        self.assertGreater(up_count, 0)
    
    @patch('src.indicators.trend.yf.Ticker')
    @patch('src.indicators.trend.get_trend_analysis_config')
    def test_analyze_trend_down(self, mock_get_config, mock_ticker):
        """测试下跌趋势分析"""
        mock_get_config.return_value = self.test_config
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.create_test_data("down")
        mock_ticker.return_value = mock_ticker_instance
        
        result = analyze_trend("AAPL", user_email="test@example.com")
        
        # 验证结果
        self.assertIsInstance(result, TrendAnalysisResult)
        
        # 检查是否有下跌趋势
        down_count = result.trends.count("down")
        self.assertGreater(down_count, 0)
    
    @patch('src.indicators.trend.yf.Ticker')
    @patch('src.indicators.trend.get_trend_analysis_config')
    def test_insufficient_data(self, mock_get_config, mock_ticker):
        """测试数据不足的情况"""
        mock_get_config.return_value = self.test_config
        
        # 创建数据不足的情况
        insufficient_data = self.create_test_data("up").head(5)  # 只有5天数据
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = insufficient_data
        mock_ticker.return_value = mock_ticker_instance
        
        result = analyze_trend("AAPL", user_email="test@example.com")
        
        # 应该返回错误
        self.assertEqual(len(result.trends), 0)
        self.assertIsNotNone(result.error)
    
    @patch('src.indicators.trend.yf.Ticker')
    @patch('src.indicators.trend.get_trend_analysis_config')
    def test_custom_config_parameters(self, mock_get_config, mock_ticker):
        """测试自定义配置参数"""
        # 使用自定义配置
        custom_config = TrendAnalysisConfig(
            ema_short_period=3,
            ema_long_period=7,
            up_trend_threshold=1,  # 更低的阈值
            down_trend_threshold=1
        )
        mock_get_config.return_value = custom_config
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.create_test_data("up")
        mock_ticker.return_value = mock_ticker_instance
        
        result = analyze_trend("AAPL", user_email="test@example.com")
        
        # 验证使用了自定义配置
        self.assertIsInstance(result, TrendAnalysisResult)
        # 更低的阈值应该产生更多的趋势判断
        trend_count = len([t for t in result.trends if t != "flat"])
        self.assertGreater(trend_count, 0)
    
    @patch('src.indicators.trend.yf.Ticker')
    def test_direct_config_usage(self, mock_ticker):
        """测试直接传递配置参数"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = self.create_test_data("up")
        mock_ticker.return_value = mock_ticker_instance
        
        # 直接传递配置
        result = analyze_trend("AAPL", config=self.test_config)
        
        self.assertIsInstance(result, TrendAnalysisResult)
        self.assertEqual(result.symbol, "AAPL")


if __name__ == "__main__":
    unittest.main()