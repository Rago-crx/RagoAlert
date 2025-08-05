#!/usr/bin/env python3
"""
开发环境启动脚本
快速启动RagoAlert开发环境的便捷脚本
"""

import os
import sys
import subprocess
import argparse
import time
import signal

def setup_dev_environment():
    """设置开发环境"""
    print("🔧 设置开发环境...")
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 开发配置文件路径（直接使用根目录的配置文件）
    dev_users_config = os.path.join(project_root, "users_config.yaml")
    dev_system_config = os.path.join(project_root, "system_config.yaml")
    
    # 检查配置文件是否存在
    if not os.path.exists(dev_users_config):
        print(f"❌ 用户配置文件不存在: {dev_users_config}")
        print("请确保项目根目录下存在 users_config.yaml 文件")
        return False
    
    if not os.path.exists(dev_system_config):
        print(f"❌ 系统配置文件不存在: {dev_system_config}")
        print("请确保项目根目录下存在 system_config.yaml 文件")
        return False
    
    # 设置环境变量指向根目录配置文件
    os.environ["RAGOALERT_CONFIG"] = dev_users_config
    os.environ["RAGOALERT_SYSTEM_CONFIG"] = dev_system_config
    
    print(f"✅ 开发环境变量已设置:")
    print(f"   RAGOALERT_CONFIG = {dev_users_config}")
    print(f"   RAGOALERT_SYSTEM_CONFIG = {dev_system_config}")
    return True

def run_tests():
    """运行测试"""
    print("🧪 运行开发环境测试...")
    
    result = subprocess.run([
        sys.executable, "tests/run_tests.py", "--deps", "--config", "--quick"
    ], capture_output=False)
    
    return result.returncode == 0

def generate_test_data():
    """生成测试数据"""
    print("📊 生成测试数据...")
    
    result = subprocess.run([
        sys.executable, "tests/test_data_generator.py"
    ], capture_output=False)
    
    return result.returncode == 0

def start_web_service():
    """启动Web服务"""
    print("🌐 启动Web服务...")
    print("访问地址: http://localhost:9797")
    print("按 Ctrl+C 停止服务")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "uvicorn", "src.web_api:app", "--host", "0.0.0.0", "--port", "8080"
        ], capture_output=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n🛑 Web服务已停止")
        return True

def start_monitoring():
    """启动监控服务"""
    print("📈 启动监控服务...")
    print("按 Ctrl+C 停止服务")
    
    try:
        result = subprocess.run([
            sys.executable, "main.py"
        ], capture_output=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n🛑 监控服务已停止")
        return True

def run_development_mode():
    """运行开发模式（同时启动Web和监控）"""
    print("🚀 启动完整开发环境...")
    print("Web界面: http://localhost:8080")
    print("按 Ctrl+C 停止所有服务")
    
    # 启动进程列表
    processes = []
    
    try:
        # 启动Web服务
        web_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "src.web_api:app", "--host", "0.0.0.0", "--port", "8080"
        ])
        processes.append(("Web服务", web_process))
        
        # 等待一秒让Web服务启动
        time.sleep(1)
        
        # 启动监控服务
        monitor_process = subprocess.Popen([
            sys.executable, "main.py"
        ])
        processes.append(("监控服务", monitor_process))
        
        print("✅ 所有服务已启动")
        
        # 等待用户中断
        while True:
            time.sleep(1)
            
            # 检查进程是否还在运行
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name}意外退出")
                    raise KeyboardInterrupt
                    
    except KeyboardInterrupt:
        print("\n🛑 停止所有服务...")
        
        # 优雅地停止所有进程
        for name, process in processes:
            if process.poll() is None:
                print(f"  停止{name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"  强制停止{name}...")
                    process.kill()
        
        print("✅ 所有服务已停止")
        return True

def show_dev_status():
    """显示开发环境状态"""
    print("📊 开发环境状态")
    print("=" * 50)
    
    # 检查配置文件
    config_files = ["users_config.yaml", "system_config.yaml"]
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {config_file}")
        else:
            print(f"❌ {config_file} (缺失)")
    
    # 检查配置模板
    template_file = "src/config/config_template.yaml"
    if os.path.exists(template_file):
        print(f"✅ {template_file}")
    else:
        print(f"❌ {template_file} (缺失)")
    
    # 检查测试文件
    test_files = ["tests/run_tests.py", "tests/quick_test.py", "tests/test_data_generator.py"]
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file} (缺失)")
    
    # 检查测试数据缓存
    if os.path.exists("test_data_cache"):
        cache_files = os.listdir("test_data_cache")
        print(f"📁 测试数据缓存: {len(cache_files)}个文件")
    else:
        print("📁 测试数据缓存: 无")
    
    # 检查依赖项
    print("\n📦 依赖项检查:")
    required_packages = ["yaml", "fastapi", "uvicorn", "pandas", "yfinance"]
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (缺失)")

def main():
    parser = argparse.ArgumentParser(description="RagoAlert 开发环境管理")
    parser.add_argument("--setup", action="store_true", help="设置开发环境")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--generate-data", action="store_true", help="生成测试数据")
    parser.add_argument("--web", action="store_true", help="只启动Web服务")
    parser.add_argument("--monitor", action="store_true", help="只启动监控服务")
    parser.add_argument("--dev", action="store_true", help="启动完整开发环境")
    parser.add_argument("--status", action="store_true", help="显示开发环境状态")
    
    args = parser.parse_args()
    
    # 如果没有指定参数，显示帮助和状态
    if not any(vars(args).values()):
        show_dev_status()
        print("\n使用示例:")
        print("  python dev_start.py --setup          # 设置开发环境")
        print("  python dev_start.py --generate-data  # 生成测试数据")
        print("  python dev_start.py --test           # 运行测试")
        print("  python dev_start.py --dev            # 启动完整开发环境")
        print("  python dev_start.py --web            # 只启动Web服务")
        print("  python dev_start.py --monitor        # 只启动监控服务")
        return 0
    
    success = True
    
    if args.status:
        show_dev_status()
    
    if args.setup:
        success &= setup_dev_environment()
    
    if args.generate_data:
        success &= generate_test_data()
    
    if args.test:
        if not setup_dev_environment():
            return 1
        success &= run_tests()
    
    if args.web:
        if not setup_dev_environment():
            return 1
        success &= start_web_service()
    
    if args.monitor:
        if not setup_dev_environment():
            return 1
        success &= start_monitoring()
    
    if args.dev:
        if not setup_dev_environment():
            return 1
        success &= run_development_mode()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())