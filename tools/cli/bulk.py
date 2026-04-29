"""Bulk operations — batch update labels, priorities, statuses with mandatory dry-run."""
from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira import operations, queries


console = Console()
MAX_BATCH = 50


def _get_client() -> JiraClient:
    try:
        return JiraClient(get_config())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _preview_issues(issues, action_desc: str) -> None:
    table = Table(title=f"Dry Run — {action_desc} ({len(issues)} issues)")
    table.add_column("Key", style="bold")
    table.add_column("Status", style="cyan")
    table.add_column("Summary")
    for issue in issues:
        table.add_row(issue.key, issue.status, issue.summary[:60])
    console.print(table)


@click.group()
def cli():
    """Bulk operations on Jira issues. Always preview with --dry-run first."""
    pass


@cli.command()
@click.option("--jql", required=True, help="JQL to select issues")
@click.option("--status", required=True, help="Target status to transition to")
@click.option("--comment", default=None, help="Comment to add with transition")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--confirm", is_flag=True, help="Execute without interactive prompt")
def transition(jql, status, comment, dry_run, confirm):
    """Bulk transition issues to a new status."""
    client = _get_client()

    with console.status("Fetching issues..."):
        issues = queries.search(client, jql, max_results=MAX_BATCH)

    if not issues:
        console.print("[dim]No issues match the query.[/dim]")
        return

    _preview_issues(issues, f"Transition to '{status}'")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not confirm and not click.confirm(f"\nTransition {len(issues)} issues to '{status}'?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    success, failed = 0, 0
    with console.status("Transitioning issues..."):
        for issue in issues:
            try:
                operations.transition_issue(client, issue.key, status, comment)
                success += 1
            except Exception as e:
                console.print(f"[red]Failed[/red] {issue.key}: {e}")
                failed += 1

    console.print(f"\n[green]{success} transitioned[/green], [red]{failed} failed[/red]")


@cli.command()
@click.option("--jql", required=True, help="JQL to select issues")
@click.option("--add-label", multiple=True, help="Labels to add")
@click.option("--remove-label", multiple=True, help="Labels to remove")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--confirm", is_flag=True, help="Execute without interactive prompt")
def label(jql, add_label, remove_label, dry_run, confirm):
    """Bulk add or remove labels."""
    client = _get_client()

    if not add_label and not remove_label:
        console.print("[red]Specify --add-label and/or --remove-label[/red]")
        return

    with console.status("Fetching issues..."):
        issues = queries.search(client, jql, max_results=MAX_BATCH)

    if not issues:
        console.print("[dim]No issues match the query.[/dim]")
        return

    action = []
    if add_label:
        action.append(f"add labels: {', '.join(add_label)}")
    if remove_label:
        action.append(f"remove labels: {', '.join(remove_label)}")

    _preview_issues(issues, "; ".join(action))

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not confirm and not click.confirm(f"\nUpdate labels on {len(issues)} issues?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    success, failed = 0, 0
    with console.status("Updating labels..."):
        for issue in issues:
            try:
                if add_label:
                    operations.add_labels(client, issue.key, list(add_label))
                if remove_label:
                    operations.remove_labels(client, issue.key, list(remove_label))
                success += 1
            except Exception as e:
                console.print(f"[red]Failed[/red] {issue.key}: {e}")
                failed += 1

    console.print(f"\n[green]{success} updated[/green], [red]{failed} failed[/red]")


@cli.command()
@click.option("--jql", required=True, help="JQL to select issues")
@click.option("--assignee", required=True, help="Assignee email")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--confirm", is_flag=True, help="Execute without interactive prompt")
def assign(jql, assignee, dry_run, confirm):
    """Bulk assign issues to a user."""
    client = _get_client()

    with console.status("Fetching issues..."):
        issues = queries.search(client, jql, max_results=MAX_BATCH)

    if not issues:
        console.print("[dim]No issues match the query.[/dim]")
        return

    _preview_issues(issues, f"Assign to '{assignee}'")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not confirm and not click.confirm(f"\nAssign {len(issues)} issues to '{assignee}'?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    success, failed = 0, 0
    with console.status("Assigning issues..."):
        for issue in issues:
            try:
                operations.update_issue(client, issue.key, {"assignee": assignee})
                success += 1
            except Exception as e:
                console.print(f"[red]Failed[/red] {issue.key}: {e}")
                failed += 1

    console.print(f"\n[green]{success} assigned[/green], [red]{failed} failed[/red]")


@cli.command()
@click.option("--jql", required=True, help="JQL to select issues")
@click.option("--priority", required=True, help="New priority (e.g., High, Normal, Low)")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--confirm", is_flag=True, help="Execute without interactive prompt")
def priority(jql, priority, dry_run, confirm):
    """Bulk update issue priority."""
    client = _get_client()

    with console.status("Fetching issues..."):
        issues = queries.search(client, jql, max_results=MAX_BATCH)

    if not issues:
        console.print("[dim]No issues match the query.[/dim]")
        return

    _preview_issues(issues, f"Set priority to '{priority}'")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not confirm and not click.confirm(f"\nUpdate priority on {len(issues)} issues?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    success, failed = 0, 0
    with console.status("Updating priorities..."):
        for issue in issues:
            try:
                operations.update_issue(client, issue.key, {"priority": priority})
                success += 1
            except Exception as e:
                console.print(f"[red]Failed[/red] {issue.key}: {e}")
                failed += 1

    console.print(f"\n[green]{success} updated[/green], [red]{failed} failed[/red]")


def main():
    cli()


if __name__ == "__main__":
    main()
