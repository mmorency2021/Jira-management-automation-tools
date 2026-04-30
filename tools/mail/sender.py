"""SMTP email sender for JiraOps reports."""
from __future__ import annotations

import smtplib
import socket
from email.mime.text import MIMEText


def send_report(
    to: str,
    subject: str,
    body_markdown: str,
    *,
    smtp_host: str = "localhost",
    smtp_port: int = 25,
    smtp_user: str = "",
    smtp_password: str = "",
    from_addr: str = "",
) -> None:
    """Send a markdown report via SMTP.

    With no user/password, connects to localhost (Postfix) without auth.
    With credentials, uses STARTTLS for secure authenticated delivery.
    """
    sender = from_addr or smtp_user or f"jiraops@{socket.gethostname()}"

    msg = MIMEText(body_markdown, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    if smtp_user and smtp_password:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender, [to], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.sendmail(sender, [to], msg.as_string())
