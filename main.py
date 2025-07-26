# run_monitors.py
from monitors.trend_monitor import TrendMonitor
from monitors.fluctuation_monitor import FluctuationMonitor
import threading
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime

if __name__ == "__main__":
    logging.info("启动所有监控器...")

    scheduler = BackgroundScheduler()

    # 调度波动监控器 (每分钟运行一次)
    # 波动监控器内部有自己的循环和时间判断，所以可以直接在一个线程中启动
    fluctuation_thread = threading.Thread(target=FluctuationMonitor.run)
    fluctuation_thread.daemon = True  # 设置为守护线程，主程序退出时它也会退出
    fluctuation_thread.start()
    logging.info("波动监控器已启动。")

    # 调度趋势监控器
    # 趋势监控器现在是按需执行，我们使用 APScheduler 在特定时间调用它
    # 假设美股盘前 UTC 13:00 (夏令时) / 14:00 (冬令时)
    # 假设美股盘后 UTC 21:00 (夏令时) / 22:00 (冬令时)
    # 注意：这里的小时是 UTC 时间

    # 每天在 UTC 13:00 和 21:00 附近运行趋势监控 (夏令时示例)
    # 你需要根据实际的夏令时/冬令时转换来调整这些时间qui
    # 更精确的做法是在 TrendMonitor.run() 内部判断当前是夏令时还是冬令时，然后根据当前时间决定是否执行
    # 我们已经将这个逻辑放到了 TrendMonitor.run() 内部，所以这里可以简单地每小时或每半小时调用一次 run()
    # 让 run() 内部的逻辑去判断是否是正确的执行时间点。

    # 为了确保在目标时间点附近能被触发，可以设置一个更频繁的调度，例如每30分钟检查一次
    scheduler.add_job(TrendMonitor.run, 'interval', minutes=30, id='trend_monitor_job')
    logging.info("趋势监控器调度已设置 (每30分钟检查一次执行时间)。")

    scheduler.start()
    logging.info("调度器已启动。")

    try:
        # 保持主线程运行，以便调度器和子线程可以继续工作
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("程序已关闭。")
