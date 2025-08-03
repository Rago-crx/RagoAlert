#!/usr/bin/env python3
"""
测试运行器
提供多种测试运行选项
"""

import os
import sys
import subprocess
import argparse
import time

def run_unit_tests():
    """运行单元测试"""
    print("🧪 运行单元测试...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest未安装，尝试使用unittest...")
        # 回退到unittest
        return run_unittest()

def run_unittest():
    """使用unittest运行测试"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "unittest", "discover", 
            "-s", "tests", "-p", "test_*.py", "-v"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 单元测试运行失败: {e}")
        return False

def run_quick_test():
    """运行快速验证测试"""
    print("⚡ 运行快速验证测试...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/quick_test.py"
        ], capture_output=False, text=True)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 快速测试运行失败: {e}")
        return False

def check_dependencies():
    """检查依赖项"""
    print("📦 检查依赖项...")
    
    required_packages = [
        "yaml", "fastapi", "uvicorn", "pandas", "numpy", 
        "yfinance", "pandas_ta", "requests"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (缺失)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺失包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("✅ 所有依赖项都已安装")
        return True

def run_syntax_check():
    """运行语法检查"""
    print("📝 运行语法检查...")
    
    python_files = []
    for root, dirs, files in os.walk("."):
        # 跳过虚拟环境和缓存目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__']]
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            compile(source, file_path, 'exec')
            print(f"  ✅ {file_path}")
        except SyntaxError as e:
            print(f"  ❌ {file_path}: {e}")
            errors.append((file_path, str(e)))
        except Exception as e:
            print(f"  ⚠️  {file_path}: {e}")
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 个语法错误")
        return False
    else:
        print("✅ 所有Python文件语法正确")
        return True

def run_config_test():
    """运行配置测试"""
    print("⚙️  运行配置测试...")
    
    try:
        # 测试配置文件模板
        if os.path.exists("config/config_template.yaml"):
            print("  ✅ 配置模板文件存在")
        else:
            print("  ❌ 配置模板文件缺失")
            return False
        
        # 测试配置管理器导入
        sys.path.append(".")
        from config.config_manager import config_manager
        print("  ✅ 配置管理器导入成功")
        
        # 测试默认配置
        system_config = config_manager.system_config
        print(f"  ✅ 系统配置加载: 端口{system_config.web_port}")
        
        # 测试股票池
        pools = system_config.stock_pools
        print(f"  ✅ 股票池配置: {len(pools)}个股票池")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置测试失败: {e}")
        return False

def run_performance_test():
    """运行性能测试"""
    print("🚀 运行性能测试...")
    
    try:
        sys.path.append(".")
        
        # 测试配置管理器性能
        start_time = time.time()
        from config.config_manager import config_manager
        config_load_time = time.time() - start_time
        print(f"  ⏱️  配置加载耗时: {config_load_time:.3f}秒")
        
        # 测试数据获取性能
        start_time = time.time()
        from src.data.yahoo import get_current_price
        price = get_current_price("AAPL")
        price_fetch_time = time.time() - start_time
        print(f"  ⏱️  价格获取耗时: {price_fetch_time:.3f}秒 (AAPL: ${price:.2f})")
        
        # 测试趋势分析性能
        start_time = time.time()
        from src.indicators.trend import analyze_trend
        result = analyze_trend("AAPL", window=5)
        trend_analysis_time = time.time() - start_time
        print(f"  ⏱️  趋势分析耗时: {trend_analysis_time:.3f}秒")
        
        # 性能评估
        total_time = config_load_time + price_fetch_time + trend_analysis_time
        print(f"  📊 总耗时: {total_time:.3f}秒")
        
        if total_time < 10:
            print("  ✅ 性能测试通过")
            return True
        else:
            print("  ⚠️  性能较慢，可能需要优化")
            return False
        
    except Exception as e:
        print(f"  ❌ 性能测试失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="RagoAlert 测试运行器")
    parser.add_argument("--quick", action="store_true", help="运行快速验证测试")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--syntax", action="store_true", help="运行语法检查")
    parser.add_argument("--config", action="store_true", help="运行配置测试")
    parser.add_argument("--deps", action="store_true", help="检查依赖项")
    parser.add_argument("--perf", action="store_true", help="运行性能测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    
    args = parser.parse_args()
    
    # 如果没有指定参数，默认运行快速测试
    if not any(vars(args).values()):
        args.quick = True
    
    print("🧪 RagoAlert 测试运行器")
    print("=" * 50)
    
    success = True
    
    if args.all or args.deps:
        success &= check_dependencies()
        print()
    
    if args.all or args.syntax:
        success &= run_syntax_check()
        print()
    
    if args.all or args.config:
        success &= run_config_test()
        print()
    
    if args.all or args.unit:
        success &= run_unit_tests()
        print()
    
    if args.all or args.quick:
        success &= run_quick_test()
        print()
    
    if args.all or args.perf:
        success &= run_performance_test()
        print()
    
    print("=" * 50)
    if success:
        print("🎉 所有测试完成！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())