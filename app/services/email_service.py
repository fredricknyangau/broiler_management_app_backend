import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import sys

from app.config import settings

class EmailService:
    @staticmethod
    def send_email(
        recipients: List[str],
        subject: str,
        content: str
    ):
        """
        Sends an email using the configured SMTP server.
        Assuming synchronous smtplib usage intended for background tasks.
        """
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            print(f"MOCK EMAIL SENT TO {recipients}: {subject}")
            print(content)
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(content, 'html'))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send email: {e}", file=sys.stderr)
