import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Tuple, Dict
from config import gmail_password, gmail_address


def build_trend_email_content(trends: Dict[str, str], changes: Dict[str, Tuple[str, str]]) -> str:
    """
    构建 HTML 邮件内容
    :param trends: 所有股票的当前趋势 {symbol: trend}
    :param changes: 发生趋势变化的股票 {symbol: (old_trend, new_trend)}
    :return: HTML 内容字符串
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
        <tr><th>股票</th><th>趋势</th><th>变化</th></tr>
    """

    # 优先放入变化的股票
    sorted_symbols = sorted(trends.keys(), key=lambda sym: sym in changes, reverse=True)

    for symbol in sorted_symbols:
        trend = trends[symbol]
        color = color_for_trend(trend)
        change_info = ""

        if symbol in changes:
            prev, curr = changes[symbol]
            change_info = f"{prev} → <b style='color:{color}'>{curr}</b>"

        html += f"<tr><td>{symbol}</td><td><span style='color:{color}'>{trend}</span></td><td>{change_info}</td></tr>"

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
