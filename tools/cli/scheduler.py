"""Built-in scheduler daemon for automatic JiraOps email reports."""
from __future__ import annotations

import signal
import sys
import time
from datetime import date

import click


_running = True


def _handle_signal(signum, frame):
    global _running
    click.echo(f"\nReceived signal {signum}, shutting down...")
    _running = False


def _run_standup():
    """Send the daily standup email. Catches all exceptions so the scheduler keeps running."""
    try:
        from tools.jira.client import JiraClient
        from tools.jira.config import get_config, reset_config
        from tools.jira.formatters import format_markdown_standup
        from tools.jira.reports import standup_report
        from tools.mail.sender import send_report

        reset_config()
        config = get_config()

        if not config.email_recipient:
            click.echo("[scheduler] No email recipient configured, skipping standup.")
            return

        client = JiraClient(config)
        report = standup_report(client, config)
        body = format_markdown_standup(
            report["my_issues"],
            report["stale"],
            report["blocked"],
            report["recently_closed"],
            report.get("watched"),
        )

        subject = f"JiraOps Standup — {date.today().isoformat()}"
        send_report(
            to=config.email_recipient,
            subject=subject,
            body_markdown=body,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            from_addr=config.email_from,
        )
        click.echo(f"[scheduler] Standup sent to {config.email_recipient}")
    except Exception as e:
        click.echo(f"[scheduler] Standup email failed: {e}", err=True)


def _run_quarterly():
    """Send the quarterly report if today is the configured day in a quarter-end month."""
    try:
        from tools.jira.client import JiraClient
        from tools.jira.config import get_config, reset_config
        from tools.jira.formatters import format_quarterly_detailed
        from tools.jira.reports import quarterly_report
        from tools.mail.sender import send_report

        reset_config()
        config = get_config()

        today = date.today()
        if today.month not in (3, 6, 9, 12):
            return
        if today.day != config.scheduler_quarterly_day:
            return

        if not config.email_recipient:
            click.echo("[scheduler] No email recipient configured, skipping quarterly.")
            return

        quarter_map = {3: "Q1", 6: "Q2", 9: "Q3", 12: "Q4"}
        quarter = quarter_map[today.month]
        year = today.year

        quarters_dates = {
            "Q1": ("01-01", "03-31"),
            "Q2": ("04-01", "06-30"),
            "Q3": ("07-01", "09-30"),
            "Q4": ("10-01", "12-31"),
        }
        start_md, end_md = quarters_dates[quarter]
        start_date = f"{year}-{start_md}"
        end_date = f"{year}-{end_md}"

        client = JiraClient(config)
        report = quarterly_report(client, config, start_date, end_date)
        body = format_quarterly_detailed(report, quarter, year)

        if config.llm_provider:
            from tools.llm.narrative import generate_narrative

            ai_text = generate_narrative(
                report,
                config.llm_provider,
                config.llm_model,
                ollama_base_url=config.ollama_base_url,
                openai_api_key=config.openai_api_key,
                anthropic_api_key=config.anthropic_api_key,
            )
            if ai_text:
                body = ai_text

        subject = f"JiraOps Quarterly Report — {quarter} {year}"
        send_report(
            to=config.email_recipient,
            subject=subject,
            body_markdown=body,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            from_addr=config.email_from,
        )
        click.echo(f"[scheduler] Quarterly report ({quarter} {year}) sent to {config.email_recipient}")
    except Exception as e:
        click.echo(f"[scheduler] Quarterly email failed: {e}", err=True)


@click.command()
@click.option("--standup-time", default=None, help="Override standup send time (HH:MM)")
@click.option("--no-standup", is_flag=True, help="Disable daily standup emails")
@click.option("--no-quarterly", is_flag=True, help="Disable quarterly report emails")
def main(standup_time, no_standup, no_quarterly):
    """Run the JiraOps email scheduler daemon.

    Sends daily standup reports and quarterly summaries on schedule.
    Runs in the foreground — use systemd, launchd, or nohup for background operation.
    """
    try:
        import schedule
    except ImportError:
        raise click.ClickException(
            "The 'schedule' package is required. Install with: pip install schedule"
        )

    from tools.jira.config import get_config

    config = get_config()
    send_time = standup_time or config.scheduler_standup_time

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if not no_standup:
        schedule.every().day.at(send_time).do(_run_standup)
        click.echo(f"[scheduler] Daily standup scheduled at {send_time}")

    if not no_quarterly:
        schedule.every().day.at("08:00").do(_run_quarterly)
        click.echo(f"[scheduler] Quarterly check runs daily (sends on day {config.scheduler_quarterly_day} of quarter-end months)")

    if no_standup and no_quarterly:
        click.echo("[scheduler] All jobs disabled. Nothing to do.")
        return

    if config.email_recipient:
        click.echo(f"[scheduler] Reports will be sent to: {config.email_recipient}")
    else:
        click.echo("[scheduler] Warning: No JIRAOPS_EMAIL_RECIPIENT configured!")

    click.echo("[scheduler] Running... (Ctrl+C to stop)")

    while _running:
        schedule.run_pending()
        time.sleep(30)

    click.echo("[scheduler] Stopped.")
