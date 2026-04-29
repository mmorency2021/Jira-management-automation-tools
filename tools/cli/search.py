"""Search and filter Jira issues."""
from __future__ import annotations

import sys

import click
from rich.console import Console

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import format_standup_table, format_stale_table
from tools.jira import queries


console = Console()


def _get_client() -> JiraClient:
    try:
        return JiraClient(get_config())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option("--project", default=None, help="Project key (e.g., NGC)")
@click.option("--status", default=None, help="Filter by status (e.g., 'In Progress')")
@click.option("--assignee", default=None, help="Filter by assignee email")
@click.option("--label", default=None, help="Filter by label")
@click.option("--component", default=None, help="Filter by component")
@click.option("--type", "issue_type", default=None, help="Filter by issue type (Bug, Task, Story, Epic)")
@click.option("--jql", default=None, help="Raw JQL query (overrides other filters)")
@click.option("--stale", is_flag=True, help="Show stale issues only")
@click.option("--max", "max_results", default=50, help="Maximum results (default 50)")
def main(project, status, assignee, label, component, issue_type, jql, stale, max_results):
    """Search Jira issues with filters or raw JQL."""
    client = _get_client()
    config = get_config()

    if stale:
        proj_list = [project] if project else config.active_projects
        if not proj_list:
            console.print("[red]Specify --project or set JIRA_ACTIVE_PROJECTS in .env[/red]")
            return
        with console.status("Fetching stale issues..."):
            issues = queries.stale_issues(client, proj_list, config.stale_threshold_days)
        if not issues:
            console.print("[dim]No stale issues found.[/dim]")
            return
        console.print(format_stale_table(issues, config.stale_threshold_days))
        console.print(f"\n[dim]{len(issues)} stale issues[/dim]")
        return

    if jql:
        query = jql
    else:
        clauses = []
        if project:
            clauses.append(f"project = {project}")
        if status:
            clauses.append(f'status = "{status}"')
        if assignee:
            if assignee == "me":
                clauses.append("assignee = currentUser()")
            else:
                clauses.append(f'assignee = "{assignee}"')
        if label:
            clauses.append(f"labels = {label}")
        if component:
            clauses.append(f'component = "{component}"')
        if issue_type:
            clauses.append(f'issuetype = "{issue_type}"')

        if not clauses:
            proj_list = config.active_projects
            if proj_list:
                proj_jql = ", ".join(proj_list)
                clauses.append(f"project IN ({proj_jql})")
            clauses.append("statusCategory != Done")

        query = " AND ".join(clauses) + " ORDER BY updated DESC"

    with console.status("Searching..."):
        issues = queries.search(client, query, max_results=max_results)

    if not issues:
        console.print("[dim]No issues found.[/dim]")
        return

    console.print(format_standup_table(issues, title="Search Results"))
    console.print(f"\n[dim]{len(issues)} issues[/dim]")


if __name__ == "__main__":
    main()
