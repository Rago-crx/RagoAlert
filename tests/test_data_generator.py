#!/usr/bin/env python3
"""
测试数据生成器
为开发和测试环境生成模拟的股价数据
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self, cache_dir: str = "test_data_cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def generate_price_data(self, 
                          symbol: str, 
                          days: int = 100, 
                          trend_type: str = "random",
                          volatility: float = 0.02,
                          start_price: float = 100.0) -> pd.DataFrame:
        """
        生成模拟股价数据
        
        Args:
            symbol: 股票代码
            days: 生成天数
            trend_type: 趋势类型 ("up", "down", "flat", "random", "volatile")
            volatility: 波动率
            start_price: 起始价格
        """
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=days),
            end=datetime.now(),
            freq='D'
        )
        
        prices = []
        current_price = start_price
        
        for i in range(len(dates)):
            # 基础趋势
            if trend_type == "up":
                trend = 0.001  # 每天0.1%上涨
            elif trend_type == "down":
                trend = -0.001  # 每天0.1%下跌
            elif trend_type == "volatile":
                trend = np.sin(i / 10) * 0.005  # 波浪式变化
            else:
                trend = 0  # 平盘或随机
            
            # 随机波动
            random_change = np.random.normal(0, volatility)
            
            # 计算新价格
            price_change = trend + random_change
            current_price *= (1 + price_change)
            
            # 确保价格为正
            current_price = max(current_price, 1.0)
            
            prices.append(current_price)
        
        # 生成OHLC数据
        df_data = []
        for i, price in enumerate(prices):
            # High: 当日最高价 (在收盘价基础上+/-2%)
            high = price * (1 + np.random.uniform(0, 0.02))
            # Low: 当日最低价 (在收盘价基础上-2%到0%)
            low = price * (1 - np.random.uniform(0, 0.02))
            # Open: 开盘价 (在最高最低之间)
            open_price = np.random.uniform(low, high)
            
            # 确保价格逻辑正确
            high = max(high, price, open_price, low)
            low = min(low, price, open_price, high)
            
            # Volume: 随机成交量
            volume = np.random.randint(1000000, 10000000)
            
            df_data.append({
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': price,
                'Volume': volume
            })
        
        df = pd.DataFrame(df_data, index=dates)
        
        # 缓存数据
        cache_file = os.path.join(self.cache_dir, f"{symbol}_{trend_type}_{days}d.csv")
        df.to_csv(cache_file)
        
        return df
    
    def generate_test_scenarios(self) -> Dict[str, Dict]:
        """生成各种测试场景的数据"""
        scenarios = {
            "strong_uptrend": {
                "description": "强上涨趋势",
                "symbols": ["TEST_UP1", "TEST_UP2"],
                "trend_type": "up",
                "volatility": 0.015,
                "days": 30
            },
            "strong_downtrend": {
                "description": "强下跌趋势", 
                "symbols": ["TEST_DOWN1", "TEST_DOWN2"],
                "trend_type": "down",
                "volatility": 0.02,
                "days": 30
            },
            "high_volatility": {
                "description": "高波动率",
                "symbols": ["TEST_VOL1", "TEST_VOL2"],
                "trend_type": "volatile",
                "volatility": 0.05,
                "days": 20
            },
            "sideways_market": {
                "description": "横盘市场",
                "symbols": ["TEST_FLAT1", "TEST_FLAT2"],
                "trend_type": "flat",
                "volatility": 0.01,
                "days": 50
            }
        }
        
        # 为每个场景生成数据
        for scenario_name, config in scenarios.items():
            print(f"🔄 生成{config['description']}数据...")
            for symbol in config["symbols"]:
                df = self.generate_price_data(
                    symbol=symbol,
                    days=config["days"],
                    trend_type=config["trend_type"],
                    volatility=config["volatility"],
                    start_price=np.random.uniform(50, 200)
                )
                print(f"  ✅ {symbol}: {len(df)}天数据")
        
        return scenarios
    
    def generate_fluctuation_test_data(self) -> List[Dict]:
        """生成波动测试数据"""
        test_cases = []
        
        # 大幅上涨场景
        test_cases.append({
            "name": "大幅上涨5%",
            "symbol": "TEST_UP_5PCT",
            "initial_price": 100.0,
            "final_price": 105.0,
            "time_minutes": 5,
            "expected_trigger": True
        })
        
        # 大幅下跌场景
        test_cases.append({
            "name": "大幅下跌4%",
            "symbol": "TEST_DOWN_4PCT", 
            "initial_price": 100.0,
            "final_price": 96.0,
            "time_minutes": 3,
            "expected_trigger": True
        })
        
        # 小幅波动场景
        test_cases.append({
            "name": "小幅波动1%",
            "symbol": "TEST_SMALL_1PCT",
            "initial_price": 100.0,
            "final_price": 101.0,
            "time_minutes": 10,
            "expected_trigger": False
        })
        
        return test_cases
    
    def download_real_sample_data(self, symbols: List[str] = None) -> Dict[str, pd.DataFrame]:
        """下载真实股价样本数据用于测试"""
        if symbols is None:
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
        
        real_data = {}
        
        print("📡 下载真实股价数据用于测试...")
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="3mo")  # 3个月数据
                
                if not df.empty:
                    real_data[symbol] = df
                    
                    # 缓存真实数据
                    cache_file = os.path.join(self.cache_dir, f"{symbol}_real_3mo.csv")
                    df.to_csv(cache_file)
                    
                    print(f"  ✅ {symbol}: {len(df)}天真实数据")
                else:
                    print(f"  ❌ {symbol}: 数据获取失败")
                    
            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
        
        return real_data
    
    def create_mock_api_responses(self) -> Dict:
        """创建模拟API响应数据"""
        mock_responses = {
            "current_prices": {
                "AAPL": 175.50,
                "MSFT": 420.30,
                "GOOGL": 140.25,
                "TSLA": 245.80,
                "TEST_UP1": 105.25,
                "TEST_DOWN1": 94.75,
                "TEST_VOL1": 123.45
            },
            "market_status": {
                "market_is_open": False,
                "next_open": "2024-01-02 09:30:00",
                "next_close": "2024-01-02 16:00:00"
            }
        }
        
        # 保存到文件
        mock_file = os.path.join(self.cache_dir, "mock_api_responses.json")
        with open(mock_file, 'w') as f:
            json.dump(mock_responses, f, indent=2)
        
        return mock_responses
    
    def generate_test_configurations(self) -> Dict:
        """生成测试配置文件"""
        test_configs = {
            "unit_test_config": {
                "trend_analysis": {
                    "up_trend_threshold": 1,
                    "down_trend_threshold": 1,
                    "ema_short_period": 3,
                    "ema_long_period": 7
                },
                "test_symbols": ["TEST_UP1", "TEST_DOWN1", "TEST_FLAT1"]
            },
            "integration_test_config": {
                "test_users": [
                    {
                        "email": "unittest@test.com",
                        "name": "Unit Test User",
                        "fluctuation_threshold": 2.0,
                        "symbols": ["TEST_UP1", "TEST_DOWN1"]
                    }
                ]
            },
            "performance_test_config": {
                "large_symbol_list": [f"TEST_PERF_{i}" for i in range(100)],
                "concurrent_users": 10,
                "test_duration_minutes": 5
            }
        }
        
        # 保存配置
        config_file = os.path.join(self.cache_dir, "test_configurations.json")
        with open(config_file, 'w') as f:
            json.dump(test_configs, f, indent=2)
        
        return test_configs


def main():
    """主函数：生成所有测试数据"""
    print("🚀 RagoAlert 测试数据生成器")
    print("=" * 50)
    
    generator = TestDataGenerator()
    
    # 生成测试场景数据
    print("\n📊 生成测试场景数据...")
    scenarios = generator.generate_test_scenarios()
    
    # 生成波动测试数据
    print("\n📈 生成波动测试数据...")
    fluctuation_tests = generator.generate_fluctuation_test_data()
    print(f"  ✅ 生成{len(fluctuation_tests)}个波动测试场景")
    
    # 下载真实数据样本
    print("\n📡 下载真实数据样本...")
    real_data = generator.download_real_sample_data()
    
    # 创建模拟API响应
    print("\n🔧 创建模拟API响应...")
    mock_responses = generator.create_mock_api_responses()
    print("  ✅ 模拟API响应数据已生成")
    
    # 生成测试配置
    print("\n⚙️ 生成测试配置...")
    test_configs = generator.generate_test_configurations()
    print("  ✅ 测试配置文件已生成")
    
    print("\n" + "=" * 50)
    print("🎉 测试数据生成完成！")
    print(f"📁 数据保存在: {generator.cache_dir}/")
    print("\n使用方法:")
    print("1. 运行单元测试: python run_tests.py --unit")
    print("2. 运行快速验证: python run_tests.py --quick")
    print("3. 使用开发配置: RAGOALERT_CONFIG=config_dev.yaml python main.py")
    
    return 0


if __name__ == "__main__":
    exit(main())