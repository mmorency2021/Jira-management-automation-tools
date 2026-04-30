"""SMTP email sender for JiraOps reports."""
from __future__ import annotations

import platform
import smtplib
import socket
import subprocess
import sys
from email.mime.text import MIMEText


def _is_smtp_available(host: str, port: int) -> bool:
    """Check if the SMTP server is reachable."""
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _ensure_postfix(host: str, port: int) -> None:
    """If localhost SMTP is down, try to start Postfix automatically."""
    if host not in ("localhost", "127.0.0.1") or port != 25:
        return
    if _is_smtp_available(host, port):
        return

    system = platform.system()
    if system == "Darwin":
        print("Postfix is not running. Starting it (sudo required)...")
        subprocess.run(["sudo", "postfix", "start"], check=True)
    elif system == "Linux":
        print("Postfix is not running. Starting it (sudo required)...")
        try:
            subprocess.run(["sudo", "systemctl", "start", "postfix"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["sudo", "postfix", "start"], check=True)
    else:
        raise RuntimeError(
            f"SMTP server at {host}:{port} is not reachable. "
            f"Start your mail server manually."
        )

    if not _is_smtp_available(host, port):
        raise RuntimeError(
            "Postfix was started but SMTP is still not reachable on "
            f"{host}:{port}. Check your Postfix configuration."
        )
    print("Postfix started successfully.")


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
    Automatically starts Postfix if localhost:25 is unreachable.
    With credentials, uses STARTTLS for secure authenticated delivery.
    """
    _ensure_postfix(smtp_host, smtp_port)

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
