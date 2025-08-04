"""
RagoAlert 主程序
启动多用户监控系统和Web配置界面
"""

import logging
import threading
import time
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ragoalert.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

from src.multi_user_monitor import monitor_manager
from src.config.config_manager import config_manager
import uvicorn
from src.web_api import app


def start_web_service():
    """启动Web配置服务"""
    try:
        port = config_manager.system_config.web_port
        logging.info(f"启动Web配置服务，端口: {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except Exception as e:
        logging.error(f"Web服务启动失败: {e}")


def main():
    """主程序入口"""
    logging.info("=" * 50)
    logging.info("🚀 RagoAlert 多用户股票监控系统启动")
    logging.info("=" * 50)
    
    try:
        # 显示系统信息
        all_users = config_manager.get_all_users()
        logging.info(f"📊 系统状态:")
        logging.info(f"   - 注册用户数: {len(all_users)}")
        logging.info(f"   - Web管理端口: {config_manager.system_config.web_port}")
        logging.info(f"   - 日志级别: {config_manager.system_config.log_level}")
        
        if all_users:
            fluctuation_users = [email for email, user in all_users.items() if user.fluctuation.enabled]
            trend_users = [email for email, user in all_users.items() if user.trend.enabled]
            logging.info(f"   - 波动监控用户: {len(fluctuation_users)}")
            logging.info(f"   - 趋势监控用户: {len(trend_users)}")
        else:
            logging.warning("⚠️  当前没有注册用户，请通过Web界面添加用户配置")
        
        # 启动Web服务 (在后台线程)
        web_thread = threading.Thread(
            target=start_web_service,
            name="WebServiceThread",
            daemon=True
        )
        web_thread.start()
        logging.info("✅ Web配置服务已启动")
        
        # 等待Web服务启动
        time.sleep(2)
        
        # 启动多用户监控管理器
        monitor_manager.start()
        logging.info("✅ 多用户监控系统已启动")
        
        # 显示访问信息
        logging.info(f"🌐 Web管理界面: http://localhost:{config_manager.system_config.web_port}/admin")
        logging.info("📝 系统已启动完成，按 Ctrl+C 停止")
        
        # 主循环 - 保持程序运行
        while True:
            try:
                time.sleep(10)
                
                # 定期检查系统状态
                status = monitor_manager.get_status()
                if not status["running"]:
                    logging.warning("⚠️  监控系统意外停止，尝试重新启动...")
                    monitor_manager.start()
                
            except KeyboardInterrupt:
                logging.info("👋 接收到停止信号...")
                break
            except Exception as e:
                logging.error(f"主循环异常: {e}")
                time.sleep(30)  # 出错后等待30秒再继续
    
    except Exception as e:
        logging.error(f"程序启动失败: {e}")
        return 1
    
    finally:
        # 优雅关闭
        logging.info("🛑 正在停止监控系统...")
        monitor_manager.stop()
        logging.info("✅ 监控系统已停止")
        logging.info("👋 程序已退出")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())