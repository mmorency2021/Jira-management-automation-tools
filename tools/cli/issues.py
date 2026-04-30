"""Issue management CLI — view, create, update, transition, comment, link."""
from __future__ import annotations

import sys

import click
from rich.console import Console

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import format_issue_detail, format_standup_table
from tools.jira import operations, queries


console = Console()


def _get_client() -> JiraClient:
    try:
        return JiraClient(get_config())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Manage Jira issues."""
    pass


@cli.command()
@click.argument("key")
def view(key):
    """View issue details."""
    client = _get_client()
    with console.status(f"Fetching {key}..."):
        issue = operations.get_issue(client, key)
    console.print(format_issue_detail(issue))


@cli.command()
@click.option("--projects", default=None, help="Comma-separated project keys")
def mine(projects):
    """List my open issues."""
    client = _get_client()
    config = get_config()
    proj_list = projects.split(",") if projects else config.active_projects

    with console.status("Fetching issues..."):
        issues = queries.my_open_issues(client, proj_list)

    if not issues:
        console.print("[dim]No open issues found.[/dim]")
        return

    console.print(format_standup_table(issues, title="My Open Issues"))
    console.print(f"\n[dim]{len(issues)} issues[/dim]")


@cli.command()
@click.argument("key")
@click.argument("target_status")
@click.option("--comment", default=None, help="Add a comment with the transition")
def status(key, target_status, comment):
    """Transition an issue to a new status."""
    client = _get_client()

    with console.status(f"Fetching transitions for {key}..."):
        current = operations.get_issue(client, key)
        transitions = operations.get_transitions(client, key)

    console.print(f"[bold]{key}[/bold] — current status: [yellow]{current.status}[/yellow]")
    console.print(f"Available transitions: {', '.join(t.name for t in transitions)}")

    if not click.confirm(f"Transition to '{target_status}'?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    with console.status("Transitioning..."):
        updated = operations.transition_issue(client, key, target_status, comment)

    console.print(f"[green]Done.[/green] {key} is now: [bold]{updated.status}[/bold]")


@cli.command()
@click.argument("key")
@click.argument("body")
def comment(key, body):
    """Add a comment to an issue."""
    client = _get_client()
    with console.status("Adding comment..."):
        c = operations.add_comment(client, key, body)
    console.print(f"[green]Comment added[/green] to {key} (id: {c.id})")


@cli.command()
@click.option("--project", required=True, help="Project key (e.g., NGC)")
@click.option("--summary", required=True, help="Issue summary/title")
@click.option("--type", "issue_type", default="Task", help="Issue type (Task, Bug, Story, Epic)")
@click.option("--description", default=None, help="Issue description")
@click.option("--assign", default=None, help="Assignee email")
@click.option("--label", multiple=True, help="Labels (can specify multiple)")
@click.option("--parent", default=None, help="Parent issue key (for subtasks)")
@click.option("--priority", default=None, help="Priority (e.g., High, Normal, Low)")
@click.option("--generate", is_flag=True, help="Use LLM to generate description from summary")
@click.option("--llm", "llm_provider", default=None, type=click.Choice(["ollama", "openai", "anthropic"]), help="LLM provider (overrides .env)")
@click.option("--model", "llm_model", default=None, help="LLM model name")
def create(project, summary, issue_type, description, assign, label, parent, priority, generate, llm_provider, llm_model):
    """Create a new issue."""
    client = _get_client()
    config = get_config()

    if generate:
        provider = llm_provider or config.llm_provider
        if not provider:
            console.print("[red]No LLM provider configured. Use --llm or set LLM_PROVIDER in .env[/red]")
            return

        model = llm_model or config.llm_model
        console.print(f"[dim]Generating description with {provider}/{model or 'default'}...[/dim]")

        from tools.llm.narrative import generate_story
        generated = generate_story(
            summary, issue_type, provider, model,
            project=project,
            ollama_base_url=config.ollama_base_url,
            openai_api_key=config.openai_api_key,
            anthropic_api_key=config.anthropic_api_key,
        )
        if generated:
            description = generated
            console.print("\n[bold]Generated Description:[/bold]")
            console.print(description)
            console.print()
        else:
            console.print("[yellow]LLM generation failed — creating without description.[/yellow]")

    console.print(f"Creating {issue_type} in [bold]{project}[/bold]: {summary}")
    if not click.confirm("Proceed?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    with console.status("Creating issue..."):
        issue = operations.create_issue(
            client, project, summary, issue_type,
            description=description,
            assignee=assign,
            labels=list(label) if label else None,
            parent_key=parent,
            priority=priority,
        )

    console.print(f"[green]Created[/green] [bold]{issue.key}[/bold] — {issue.summary}")


@cli.command()
@click.argument("key")
@click.option("--summary", default=None, help="New summary")
@click.option("--assign", default=None, help="New assignee email")
@click.option("--priority", default=None, help="New priority")
@click.option("--add-label", multiple=True, help="Labels to add")
@click.option("--remove-label", multiple=True, help="Labels to remove")
def update(key, summary, assign, priority, add_label, remove_label):
    """Update issue fields."""
    client = _get_client()
    fields = {}
    if summary:
        fields["summary"] = summary
    if assign:
        fields["assignee"] = assign
    if priority:
        fields["priority"] = priority

    if not fields and not add_label and not remove_label:
        console.print("[dim]Nothing to update. Use --summary, --assign, --priority, --add-label, or --remove-label.[/dim]")
        return

    with console.status(f"Updating {key}..."):
        if fields:
            operations.update_issue(client, key, fields)
        if add_label:
            operations.add_labels(client, key, list(add_label))
        if remove_label:
            operations.remove_labels(client, key, list(remove_label))

        issue = operations.get_issue(client, key)

    console.print(f"[green]Updated[/green] {key}")
    console.print(format_issue_detail(issue))


@cli.command()
@click.argument("from_key")
@click.argument("to_key")
@click.option("--type", "link_type", default="Related", help="Link type (Blocks, Related, Duplicate, Depend)")
def link(from_key, to_key, link_type):
    """Link two issues."""
    client = _get_client()
    with console.status("Creating link..."):
        operations.link_issues(client, from_key, to_key, link_type)
    console.print(f"[green]Linked[/green] {from_key} —[{link_type}]→ {to_key}")


def main():
    cli()


if __name__ == "__main__":
    main()
