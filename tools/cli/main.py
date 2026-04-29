"""JiraOps — unified CLI entry point."""
import click

from tools.cli.standup import main as standup_cmd
from tools.cli.issues import cli as issues_group
from tools.cli.search import main as search_cmd
from tools.cli.deps import main as deps_cmd
from tools.cli.bulk import cli as bulk_group
from tools.cli.quarterly import main as quarterly_cmd


@click.group()
@click.version_option(version="1.0.0", prog_name="jiraops")
def cli():
    """JiraOps — Jira automation management tools."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, type=int, help="Port to listen on")
def web(host, port):
    """Launch the web dashboard."""
    from tools.web.app import app
    app.run(debug=True, host=host, port=port)


cli.add_command(standup_cmd, "standup")
cli.add_command(issues_group, "issues")
cli.add_command(search_cmd, "search")
cli.add_command(deps_cmd, "deps")
cli.add_command(bulk_group, "bulk")
cli.add_command(quarterly_cmd, "quarterly")


def main():
    cli()


if __name__ == "__main__":
    main()
