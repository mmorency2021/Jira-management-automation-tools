"""CLI commands for emailing JiraOps reports."""
from __future__ import annotations

from datetime import date

import click

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import format_markdown_standup, format_quarterly_detailed
from tools.jira.reports import standup_report, quarterly_report


def _require_recipient(to: str, config) -> str:
    recipient = to or config.email_recipient
    if not recipient:
        raise click.ClickException(
            "No recipient configured. Use --to or set JIRAOPS_EMAIL_RECIPIENT in .env"
        )
    return recipient


@click.command()
@click.option("--to", default="", help="Override recipient email address")
@click.option("--user", default=None, help="Jira user email to report on (default: yourself)")
@click.option("--dry-run", is_flag=True, help="Print email instead of sending")
def mail_standup(to, user, dry_run):
    """Send daily standup report by email."""
    config = get_config()
    recipient = _require_recipient(to, config)
    client = JiraClient(config)

    report = standup_report(client, config, user=user)
    body = format_markdown_standup(
        report["my_issues"],
        report["stale"],
        report["blocked"],
        report["recently_closed"],
        report.get("watched"),
    )

    subject = f"JiraOps Standup — {date.today().isoformat()}"

    if dry_run:
        click.echo(f"To: {recipient}")
        click.echo(f"Subject: {subject}")
        click.echo(f"---\n{body}")
        return

    from tools.mail.sender import send_report

    send_report(
        to=recipient,
        subject=subject,
        body_markdown=body,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        from_addr=config.email_from,
    )
    click.echo(f"Standup report sent to {recipient}")


@click.command()
@click.option("--to", default="", help="Override recipient email address")
@click.option("--user", default=None, help="Jira user email to report on (default: yourself)")
@click.option("--quarter", type=click.Choice(["Q1", "Q2", "Q3", "Q4"]), default=None)
@click.option("--year", type=int, default=None)
@click.option("--llm", "llm_provider", type=click.Choice(["ollama", "openai", "anthropic", "vertex"]), default=None)
@click.option("--model", "llm_model", default="")
@click.option("--dry-run", is_flag=True, help="Print email instead of sending")
def mail_quarterly(to, user, quarter, year, llm_provider, llm_model, dry_run):
    """Send quarterly report by email."""
    config = get_config()
    recipient = _require_recipient(to, config)
    client = JiraClient(config)

    today = date.today()
    if not quarter:
        month = today.month
        if month <= 3:
            quarter = "Q1"
        elif month <= 6:
            quarter = "Q2"
        elif month <= 9:
            quarter = "Q3"
        else:
            quarter = "Q4"
    if not year:
        year = today.year

    quarters_map = {
        "Q1": ("01-01", "03-31"),
        "Q2": ("04-01", "06-30"),
        "Q3": ("07-01", "09-30"),
        "Q4": ("10-01", "12-31"),
    }
    start_md, end_md = quarters_map[quarter]
    start_date = f"{year}-{start_md}"
    end_date = f"{year}-{end_md}"

    report = quarterly_report(client, config, start_date, end_date, user=user)
    body = format_quarterly_detailed(report, quarter, year)

    provider = llm_provider or config.llm_provider
    if provider:
        from tools.llm.narrative import generate_narrative

        ai_text = generate_narrative(
            report,
            provider,
            llm_model or config.llm_model,
            ollama_base_url=config.ollama_base_url,
            openai_api_key=config.openai_api_key,
            anthropic_api_key=config.anthropic_api_key,
        )
        if ai_text:
            body = ai_text
        else:
            click.echo("Warning: LLM generation failed, using template report.")

    subject = f"JiraOps Quarterly Report — {quarter} {year}"

    if dry_run:
        click.echo(f"To: {recipient}")
        click.echo(f"Subject: {subject}")
        click.echo(f"---\n{body}")
        return

    from tools.mail.sender import send_report

    send_report(
        to=recipient,
        subject=subject,
        body_markdown=body,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        from_addr=config.email_from,
    )
    click.echo(f"Quarterly report ({quarter} {year}) sent to {recipient}")
