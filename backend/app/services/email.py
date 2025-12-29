
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mailgun.org")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "postmaster@sandbox.mailgun.org")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "secret")
EMAIL_FROM = os.getenv("EMAIL_FROM", "VoiceBrain <noreply@voicebrain.ai>")

async def send_email(to_email: str, subject: str, body: str):
    """
    Sends an email using SMTP.
    Replaces the previous mock print statements.
    """
    if os.getenv("ENVIRONMENT") == "development" and not os.getenv("SMTP_PASSWORD"):
        logger.info(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
        logger.info(f"Body: {body}")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, to_email, text)
        server.quit()
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
