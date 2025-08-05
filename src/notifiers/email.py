import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Tuple, Dict, Optional

from email.mime.multipart import MIMEMultipart
from src.indicators.trend import TrendAnalysisResult
from src.indicators.fluctuation import FluctuationAnalysisResult


def build_trend_email_content(
    trends: Dict[str, TrendAnalysisResult],
    changes: Dict[str, Tuple[str, str]]
) -> str:
    """
    构建 HTML 邮件内容，展示股票趋势和技术指标。
    """

    def color_for_trend(_trend: str) -> str:
        return {
            'up': 'green',
            'down': 'red',
            'flat': 'gray',
            'unknown': 'black'
        }.get(_trend, 'black')

    def color_for_signal(_signal: str) -> str:
        return {
            'buy': 'green',
            'sell': 'red',
            'hold': 'gray'
        }.get(_signal, 'black')

    def color_for_close_price(close_price: float, bb_upper: float, bb_lower: float) -> str:
        """
        根据收盘价的位置设置颜色：
        - 上轨：绿色
        - 下轨：红色
        - 中轨：黄色
        - 上下轨之间：蓝色
        """
        if close_price > bb_upper:
            return 'green'
        elif close_price < bb_lower:
            return 'red'
        elif close_price == (bb_upper + bb_lower) / 2:
            return 'yellow'
        else:
            return 'blue'

    html = """<html><body>
        <h2>📈 股票趋势日报</h2>
        <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
        <tr>
            <th>股票</th>
            <th>当前趋势</th>
            <th>趋势变化</th>
            <th>策略建议</th>
            <th>EMA状态</th>
            <th>MACD状态</th>
            <th>ADX</th>
            <th>布林带</th>
            <th>RSI</th>
            <th>收盘价</th>
        </tr>
    """

    sorted_symbols = sorted(trends.keys(), key=lambda sym: sym in changes, reverse=True)

    for symbol in sorted_symbols:
        result = trends[symbol]
        indicator = result.indicators
        current_trend = getattr(result, 'current_trend', result.trends[-1] if result.trends else "unknown")
        signal = result.signal or "hold"
        signal_color = color_for_signal(signal)
        trend_color = color_for_trend(current_trend)

        change_info = ""
        if symbol in changes:
            prev, curr = changes[symbol]
            change_info = f"{prev} → <b style='color:{trend_color}'>{curr}</b>"

        close_price_color = color_for_close_price(
            indicator.close, indicator.bb_upper, indicator.bb_lower
        )

        html += f"""<tr>
            <td>{symbol}</td>
            <td style="color:{trend_color}"><b>{current_trend}</b></td>
            <td>{change_info}</td>
            <td style="color:{signal_color}"><b>{signal.upper()}</b></td>
            <td>{'在上方' if indicator.ema7 > indicator.ema20 else '在下方'}</td>
            <td>{"MACD柱>0 且 DIF>DEA" if indicator.macd_hist > 0 and indicator.macd > indicator.macd_signal else "弱势"}</td>
            <td>{indicator.adx:.2f}</td>
            <td>
                中轨: {indicator.bb_middle:.2f}<br>
                上轨: {indicator.bb_upper:.2f}<br>
                下轨: {indicator.bb_lower:.2f}
            </td>
            <td>{indicator.rsi:.2f}</td>
            <td style="color:{close_price_color};"><b>{indicator.close:.2f}</b></td>
        </tr>"""

    html += "</table></body></html>"
    return html

def build_fluctuation_email_content(
    results: List[FluctuationAnalysisResult] # Step 2: Accept a list of results
) -> str:
    """
    构建 HTML 邮件内容，展示股票价格波动信息。
    :param results: FluctuationAnalysisResult 对象的列表
    """
    if not results:
        return "<html><body><p>没有股票波动信息。</p></body></html>"

    html = """<html><body>
        <h2>🚨 股票价格波动提醒</h2>
        <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
        <tr>
            <th>股票代码</th>
            <th>初始价格</th>
            <th>当前价格</th>
            <th>变化类型</th>
            <th>百分比变化</th>
        </tr>
    """

    for result in results: # Step 2: Iterate through the list
        color = "green" if result.change_type == "上涨" else "red"
        html += f"""
        <tr>
            <td><b>{result.symbol}</b></td>
            <td>${result.initial_price:.2f}</td>
            <td>${result.current_price:.2f}</td>
            <td style='color:{color}'>{result.change_type}</td>
            <td style='color:{color}'>{result.percentage_change:.2f}%</td>
        </tr>
        """
    html += """</table>
        <p>请注意市场动态。</p>
        </body></html>
    """
    return html

def send_gmail(
    subject: str, 
    html_body: str, 
    to_emails: List[str],
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
    smtp_user: Optional[str] = None,
    smtp_pass: Optional[str] = None,
    sender_name: str = "RagoAlert"
):
    """
    发送Gmail邮件，支持自定义SMTP配置
    
    Args:
        subject: 邮件主题
        html_body: HTML邮件正文
        to_emails: 收件人邮箱列表
        smtp_server: SMTP服务器地址
        smtp_port: SMTP端口
        smtp_user: 发送邮箱
        smtp_pass: 邮箱密码
        sender_name: 发送者名称
    """
    if not smtp_user or not smtp_pass:
        raise ValueError("发送邮箱账号和密码不能为空")
    
    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = formataddr((sender_name, smtp_user))
    msg['To'] = ', '.join(to_emails)

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_emails, msg.as_string())
        print(f"[SUCCESS] 邮件发送成功 ✅ -> {', '.join(to_emails)}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败 ❌: {str(e)}")
        raise  # 重新抛出异常以便上层处理
