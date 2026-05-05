import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def email_is_configured():
    return all([SMTP_HOST, SMTP_USER, SMTP_PASS])

def send_email(to_email, subject, body):
    if not email_is_configured():
        print(f"[EMAIL SKIPPED] {subject} → {to_email}")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[EMAIL SENT] {to_email}: {subject}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def send_task_reminder(email, title, when):
    subject = f"Reminder: {title}"
    body = f"Your task '{title}' is due at {when}"
    return send_email(email, subject, body)