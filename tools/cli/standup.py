"""Daily standup prep — summarizes active issues, stale items, blockers."""
import json
import sys

import click
from rich.console import Console

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import (
    format_blocked_table,
    format_markdown_standup,
    format_stale_table,
    format_standup_table,
    issues_to_dicts,
)
from tools.jira.reports import standup_report


@click.command()
@click.option("--projects", default=None, help="Comma-separated project keys (overrides .env)")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "markdown", "json"]))
@click.option("--include-watched", is_flag=True, help="Include watched projects")
@click.option("--stale-days", default=None, type=int, help="Override stale threshold (days)")
@click.option("--output", default=None, type=click.Path(), help="Write to file instead of stdout")
@click.option("--user", default=None, help="Jira user email to report on (default: yourself)")
def main(projects, output_format, include_watched, stale_days, output, user):
    """Generate a daily standup report from Jira."""
    try:
        config = get_config()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if projects:
        from tools.jira.config import reset_config
        from dataclasses import replace as dc_replace
        reset_config()
        config = get_config()
        config = dc_replace(config, active_projects=[p.strip() for p in projects.split(",") if p.strip()])

    if stale_days is not None:
        from dataclasses import replace as dc_replace
        config = dc_replace(config, stale_threshold_days=stale_days)

    client = JiraClient(config)
    console = Console()

    with console.status("[bold cyan]Fetching Jira data..."):
        report = standup_report(client, config, user=user)

    if output_format == "json":
        data = {
            "summary": report["summary"],
            "issues": issues_to_dicts(report["my_issues"]),
            "stale": issues_to_dicts(report["stale"]),
            "blocked": issues_to_dicts(report["blocked"]),
            "recently_closed": issues_to_dicts(report["recently_closed"]),
        }
        if include_watched and report["watched"]:
            data["watched"] = issues_to_dicts(report["watched"])
        text = json.dumps(data, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(text)
            click.echo(f"Written to {output}")
        else:
            click.echo(text)
        return

    if output_format == "markdown":
        text = format_markdown_standup(
            report["my_issues"],
            report["stale"],
            report["blocked"],
            report["recently_closed"],
            report["watched"] if include_watched else None,
        )
        if output:
            with open(output, "w") as f:
                f.write(text)
            click.echo(f"Written to {output}")
        else:
            click.echo(text)
        return

    # Table format (default)
    summary = report["summary"]
    console.print()
    console.print(f"[bold]Daily Standup[/bold] — {summary['total_open']} open issues")
    console.print(
        f"  In Progress: {summary['in_progress']}  |  "
        f"To Do: {summary['to_do']}  |  "
        f"Stale: {summary['stale_count']}  |  "
        f"Blocked: {summary['blocked_count']}  |  "
        f"Closed this week: {summary['closed_this_week']}"
    )
    console.print()

    if report["my_issues"]:
        console.print(format_standup_table(report["my_issues"]))
        console.print()

    if report["blocked"]:
        console.print(format_blocked_table(report["blocked"]))
        console.print()

    if report["stale"]:
        console.print(format_stale_table(report["stale"], config.stale_threshold_days))
        console.print()

    if report["recently_closed"]:
        console.print(format_standup_table(report["recently_closed"], title="Recently Closed (7 days)"))
        console.print()

    if include_watched and report["watched"]:
        console.print(format_standup_table(report["watched"], title="Watched Issues (other teams)"))
        console.print()


if __name__ == "__main__":
    main()
