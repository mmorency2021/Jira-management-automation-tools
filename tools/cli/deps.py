"""Cross-project dependency tracker."""
from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.reports import dependency_report


console = Console()


def _get_client() -> JiraClient:
    try:
        return JiraClient(get_config())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option("--projects", default=None, help="Comma-separated project keys (overrides .env)")
@click.option("--type", "link_type", default=None, help="Filter by link type (e.g., Blocks, Depends)")
def main(projects, link_type):
    """Show cross-project dependencies and blockers."""
    client = _get_client()
    config = get_config()
    proj_list = projects.split(",") if projects else config.active_projects

    if not proj_list:
        console.print("[red]Specify --projects or set JIRA_ACTIVE_PROJECTS in .env[/red]")
        return

    with console.status("Analyzing dependencies..."):
        report = dependency_report(client, config)

    cross = report.get("cross_project", [])
    if link_type:
        lt = link_type.lower()
        cross = [c for c in cross if lt in c["link_type"].lower()]

    if not cross:
        console.print("[dim]No cross-project dependencies found.[/dim]")
        return

    table = Table(title="Cross-Project Dependencies", show_lines=True)
    table.add_column("Source", style="bold")
    table.add_column("Link Type", style="cyan")
    table.add_column("Target", style="bold")
    table.add_column("Target Status")
    table.add_column("Target Project", style="yellow")
    table.add_column("At Risk?")

    for dep in cross:
        risk = "[red]YES[/red]" if dep.get("at_risk") else "[green]No[/green]"
        table.add_row(
            dep["issue"],
            f"{dep['link_type']} ({dep['direction']})",
            dep["linked_key"],
            dep["linked_status"],
            dep["linked_project"],
            risk,
        )

    console.print(table)
    console.print(f"\n[dim]{len(cross)} cross-project links[/dim]")

    blocked = report.get("blocked", [])
    if blocked:
        console.print()
        bt = Table(title="Blocked Issues", show_lines=True)
        bt.add_column("Issue", style="bold red")
        bt.add_column("Summary")
        bt.add_column("Status", style="yellow")

        for issue in blocked:
            bt.add_row(issue.key, issue.summary[:60], issue.status)

        console.print(bt)
        console.print(f"\n[dim]{len(blocked)} blocked issues[/dim]")


if __name__ == "__main__":
    main()
