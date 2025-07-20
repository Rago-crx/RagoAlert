import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List

from config import gmail_password, gmail_address


def send_gmail(subject: str, body: str, to_emails: List[str]):
    # 构造邮件内容
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = formataddr(('Notifier', gmail_address))
    msg['To'] = ', '.join(to_emails)

    # SMTP 设置
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465  # SSL
    smtp_user = gmail_address
    smtp_pass = gmail_password  # 应用专用密码

    print(f"[INFO] 准备发送邮件")
    print(f"[INFO] 发件人: {smtp_user}")
    print(f"[INFO] 收件人: {', '.join(to_emails)}")
    print(f"[INFO] 邮件标题: {subject}")

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_emails, msg.as_string())
        print("[SUCCESS] 邮件发送成功 ✅")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败 ❌: {str(e)}")


# 示例用法
if __name__ == "__main__":
    recipients = ["caoruixu15@gmail.com", "example@another.com"]
    send_gmail("Gmail 通知测试", "这是一封来自 Gmail 的通知邮件", recipients)
