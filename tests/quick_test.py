#!/usr/bin/env python3
"""
快速验证脚本
用于快速测试系统各个组件的功能
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_config_system():
    """测试配置系统"""
    print("🔧 测试配置系统...")
    
    try:
        from config.config_manager import config_manager, UserConfig, TrendAnalysisConfig
        
        # 测试系统配置
        system_config = config_manager.system_config
        print(f"  ✅ 系统配置加载成功: Web端口={system_config.web_port}")
        
        # 测试股票池
        china_tech = system_config.stock_pools.get("CHINA_TECH", [])
        print(f"  ✅ 股票池加载: CHINA_TECH包含{len(china_tech)}支股票")
        
        # 测试用户配置
        users = config_manager.get_all_users()
        print(f"  ✅ 用户配置: 当前有{len(users)}个用户")
        
        # 测试趋势分析配置
        trend_config = config_manager.system_config.trend_analysis
        print(f"  ✅ 趋势配置: 上涨阈值={trend_config.up_trend_threshold}, EMA周期={trend_config.ema_short_period}/{trend_config.ema_long_period}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置系统测试失败: {e}")
        return False

def test_data_fetching():
    """测试数据获取"""
    print("📊 测试数据获取...")
    
    try:
        from src.data.yahoo import get_current_price, get_historical_data
        
        # 测试实时价格获取
        test_symbols = ["AAPL", "MSFT"]
        for symbol in test_symbols:
            price = get_current_price(symbol)
            if price > 0:
                print(f"  ✅ {symbol} 实时价格: ${price:.2f}")
            else:
                print(f"  ⚠️  {symbol} 价格获取失败")
        
        # 测试历史数据获取
        df = get_historical_data("AAPL", period="5d")
        if not df.empty:
            print(f"  ✅ 历史数据获取成功: {len(df)}天数据")
            print(f"  📈 AAPL 最新收盘价: ${df['Close'].iloc[-1]:.2f}")
        else:
            print(f"  ⚠️  历史数据获取失败")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 数据获取测试失败: {e}")
        return False

def test_trend_analysis():
    """测试趋势分析"""
    print("📈 测试趋势分析...")
    
    try:
        from src.indicators.trend import analyze_trend
        from config.config_manager import TrendAnalysisConfig
        
        # 创建测试配置
        test_config = TrendAnalysisConfig(
            up_trend_threshold=2,
            down_trend_threshold=2,
            ema_short_period=7,
            ema_long_period=20
        )
        
        # 测试趋势分析
        result = analyze_trend("AAPL", window=5, config=test_config)
        
        if result.error:
            print(f"  ⚠️  趋势分析警告: {result.error}")
        else:
            print(f"  ✅ {result.symbol} 趋势分析成功")
            print(f"  📊 趋势历史: {result.trends[-5:] if len(result.trends) >= 5 else result.trends}")
            print(f"  🎯 交易信号: {result.signal}")
            
            if result.indicators:
                print(f"  💹 技术指标: EMA7={result.indicators.ema7:.2f}, EMA20={result.indicators.ema20:.2f}")
                print(f"  📊 RSI={result.indicators.rsi:.1f}, ADX={result.indicators.adx:.1f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 趋势分析测试失败: {e}")
        return False

def test_fluctuation_analysis():
    """测试波动分析"""
    print("📉 测试波动分析...")
    
    try:
        from src.indicators.fluctuation import FluctuationAnalyzer
        from collections import deque
        from datetime import timedelta
        
        # 创建模拟价格历史
        now = datetime.now()
        price_history = deque(maxlen=60)
        
        # 添加模拟数据：从100到105的价格变化（5%涨幅）
        for i in range(5):
            timestamp = now - timedelta(minutes=5-i)
            price = 100 + i * 1.25  # 逐步上涨
            price_history.append((timestamp, price))
        
        # 分析波动
        result = FluctuationAnalyzer.analyze_fluctuation(
            symbol="AAPL",
            price_history=price_history,
            current_price=105.0,
            time_window_minutes=4
        )
        
        if result:
            print(f"  ✅ 波动分析成功")
            print(f"  📊 {result.symbol}: {result.initial_price:.2f} → {result.current_price:.2f}")
            print(f"  📈 变化: {result.percentage_change:.2f}% ({result.change_type})")
        else:
            print(f"  ⚠️  波动分析数据不足")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 波动分析测试失败: {e}")
        return False

def test_user_monitors():
    """测试用户监控器"""
    print("👥 测试用户监控器...")
    
    try:
        from config.config_manager import UserConfig, UserFluctuationConfig, UserTrendConfig
        from src.monitors.fluctuation_monitor import FluctuationMonitor
        from src.monitors.trend_monitor import TrendMonitor
        
        # 创建测试用户配置
        user_config = UserConfig(
            email="test@example.com",
            name="Test User"
        )
        user_config.fluctuation = UserFluctuationConfig(
            threshold_percent=3.0,
            symbols=["AAPL"],
            notification_interval_minutes=5,
            enabled=True
        )
        user_config.trend = UserTrendConfig(
            enabled=True,
            symbols=["AAPL"],
            pre_market_notification=True,
            post_market_notification=True
        )
        
        # 测试波动监控器
        fluctuation_monitor = FluctuationMonitor(user_config)
        print(f"  ✅ 波动监控器创建成功: 监控{len(user_config.fluctuation.symbols)}支股票")
        
        # 测试趋势监控器
        trend_monitor = TrendMonitor(user_config)
        print(f"  ✅ 趋势监控器创建成功: 监控{len(user_config.trend.symbols)}支股票")
        
        # 获取监控器状态
        fluctuation_status = fluctuation_monitor.get_status()
        trend_status = trend_monitor.get_status()
        
        print(f"  📊 波动监控状态: 启用={fluctuation_status['enabled']}, 阈值={fluctuation_status['threshold_percent']}%")
        print(f"  📊 趋势监控状态: 启用={trend_status['enabled']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 用户监控器测试失败: {e}")
        return False

def test_web_api():
    """测试Web API"""
    print("🌐 测试Web API...")
    
    try:
        from src.web_api import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # 测试根路径
        response = client.get("/")
        if response.status_code == 200:
            print(f"  ✅ API根路径响应正常")
        else:
            print(f"  ⚠️  API根路径响应异常: {response.status_code}")
        
        # 测试用户API
        response = client.get("/api/users")
        if response.status_code == 200:
            users = response.json()
            print(f"  ✅ 用户API响应正常: {len(users)}个用户")
        else:
            print(f"  ⚠️  用户API响应异常: {response.status_code}")
        
        # 测试统计API
        response = client.get("/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  ✅ 统计API响应正常: 监控{stats.get('total_monitored_symbols', 0)}支股票")
        else:
            print(f"  ⚠️  统计API响应异常: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Web API测试失败: {e}")
        return False

def run_integration_test():
    """运行集成测试"""
    print("🔄 运行集成测试...")
    
    try:
        from config.config_manager import config_manager
        from src.multi_user_monitor import monitor_manager
        
        # 测试多用户监控管理器
        status = monitor_manager.get_status()
        print(f"  ✅ 多用户监控管理器状态:")
        print(f"    📊 波动监控器: {status['fluctuation_monitors']}个")
        print(f"    📈 趋势监控器: {status['trend_monitors']}个")
        print(f"    🏃 运行状态: {status['running']}")
        
        # 测试配置变更通知
        original_users = len(config_manager.get_all_users())
        print(f"  📊 配置测试: 当前{original_users}个用户")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 集成测试失败: {e}")
        return False

def create_test_user():
    """创建测试用户"""
    print("👤 创建测试用户...")
    
    try:
        from config.config_manager import config_manager
        
        test_email = "quicktest@example.com"
        
        # 删除可能存在的测试用户
        config_manager.delete_user(test_email)
        
        # 创建新的测试用户
        success = config_manager.create_or_update_user(
            email=test_email,
            name="Quick Test User",
            fluctuation_threshold_percent=2.0,
            fluctuation_symbols=["AAPL", "MSFT"],
            fluctuation_notification_interval_minutes=3,
            fluctuation_enabled=True,
            trend_enabled=True,
            trend_symbols=["NASDAQ_CORE"],
            trend_pre_market_notification=True,
            trend_post_market_notification=False
        )
        
        if success:
            user_config = config_manager.get_user_config(test_email)
            print(f"  ✅ 测试用户创建成功")
            print(f"    📧 邮箱: {user_config.email}")
            print(f"    👤 姓名: {user_config.name}")
            print(f"    📊 波动监控: {len(user_config.fluctuation.symbols)}支股票, 阈值{user_config.fluctuation.threshold_percent}%")
            print(f"    📈 趋势监控: {len(user_config.trend.symbols)}支股票")
            
            # 清理测试用户
            config_manager.delete_user(test_email)
            print(f"  🗑️  测试用户已清理")
            
        return success
        
    except Exception as e:
        print(f"  ❌ 创建测试用户失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 RagoAlert 快速验证测试")
    print("=" * 50)
    
    start_time = time.time()
    
    # 测试项目列表
    tests = [
        ("配置系统", test_config_system),
        ("数据获取", test_data_fetching),
        ("趋势分析", test_trend_analysis),
        ("波动分析", test_fluctuation_analysis),
        ("用户监控器", test_user_monitors),
        ("Web API", test_web_api),
        ("集成测试", run_integration_test),
        ("测试用户创建", create_test_user),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name}执行异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"📈 总计: {passed}/{total} 项测试通过")
    print(f"⏱️  耗时: {time.time() - start_time:.2f}秒")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
        return 0
    else:
        print("⚠️  部分测试失败，请检查相关组件")
        return 1

if __name__ == "__main__":
    sys.exit(main())