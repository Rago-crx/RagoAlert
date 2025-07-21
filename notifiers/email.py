import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Tuple, Dict

from config import gmail_password, gmail_address
from email.mime.multipart import MIMEMultipart
from indicators.trend import TrendAnalysisResult  # 确保路径正确


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

    html = """<html><body>
        <h2>📈 股票趋势日报</h2>
        <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
        <tr>
            <th>股票</th>
            <th>当前趋势</th>
            <th>变化</th>
            <th>EMA状态</th>
            <th>MACD状态</th>
            <th>ADX</th>
            <th>布林带</th>
        </tr>
    """

    sorted_symbols = sorted(trends.keys(), key=lambda sym: sym in changes, reverse=True)

    for symbol in sorted_symbols:
        result = trends[symbol]
        color = color_for_trend(result.current_trend)
        change_info = ""
        if symbol in changes:
            prev, curr = changes[symbol]
            change_info = f"{prev} → <b style='color:{color}'>{curr}</b>"

        html += f"""<tr>
            <td>{symbol}</td>
            <td style="color:{color}"><b>{result.current_trend}</b></td>
            <td>{change_info}</td>
            <td>{'在上方' if result.above_ema else '在下方'}</td>
            <td>{"MACD柱>0 且 DIF>DEA" if result.macd_positive and result.dif_gt_dea else "弱势"}</td>
            <td>{result.adx:.2f}</td>
            <td>
                中轨: {result.bollinger_middle:.2f}<br>
                上轨: {result.bollinger_upper:.2f}<br>
                下轨: {result.bollinger_lower:.2f}
            </td>
        </tr>"""

    html += "</table></body></html>"
    return html



def send_gmail(subject: str, html_body: str, to_emails: List[str]):
    msg = MIMEText(html_body, 'html')  # 使用 HTML 内容
    msg['Subject'] = subject
    msg['From'] = formataddr(('Notifier', gmail_address))
    msg['To'] = ', '.join(to_emails)

    smtp_server = 'smtp.gmail.com'
    smtp_port = 465
    smtp_user = gmail_address
    smtp_pass = gmail_password

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_emails, msg.as_string())
        print("[SUCCESS] 邮件发送成功 ✅")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败 ❌: {str(e)}")
