"""End-of-quarter review — generate reports, export to Google Sheets/Slides."""
from __future__ import annotations

import json
import sys
from datetime import date

import click
from rich.console import Console
from rich.table import Table

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import format_quarterly_detailed, issues_to_dicts
from tools.jira.reports import quarterly_report


console = Console()

QUARTERS = {
    "Q1": ("01-01", "03-31"),
    "Q2": ("04-01", "06-30"),
    "Q3": ("07-01", "09-30"),
    "Q4": ("10-01", "12-31"),
}


def _get_quarter_dates(quarter: str, year: int) -> tuple[str, str]:
    q = quarter.upper()
    if q not in QUARTERS:
        raise click.BadParameter(f"Invalid quarter: {quarter}. Use Q1, Q2, Q3, or Q4.")
    start_md, end_md = QUARTERS[q]
    return f"{year}-{start_md}", f"{year}-{end_md}"


def _current_quarter() -> tuple[str, int]:
    today = date.today()
    month = today.month
    if month <= 3:
        return "Q1", today.year
    elif month <= 6:
        return "Q2", today.year
    elif month <= 9:
        return "Q3", today.year
    else:
        return "Q4", today.year


@click.command()
@click.option("--quarter", default=None, help="Quarter (Q1, Q2, Q3, Q4). Defaults to current.")
@click.option("--year", default=None, type=int, help="Year. Defaults to current.")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "markdown", "json"]))
@click.option("--output", default=None, type=click.Path(), help="Write to file instead of stdout")
@click.option("--export-sheets", is_flag=True, help="Export to Google Sheets")
@click.option("--export-slides", is_flag=True, help="Export to Google Slides")
@click.option("--export-xlsx", is_flag=True, help="Export to local .xlsx file")
@click.option("--export-docx", is_flag=True, help="Export to local .docx file")
@click.option("--export-pptx", is_flag=True, help="Export to local .pptx file")
@click.option("--detailed", is_flag=True, help="Generate detailed narrative report")
@click.option("--llm", "llm_provider", default=None, type=click.Choice(["ollama", "openai", "anthropic", "vertex"]), help="LLM provider for narrative analysis")
@click.option("--model", "llm_model", default=None, help="LLM model name (e.g. llama3, gpt-4o-mini, claude-sonnet-4-6)")
@click.option("--user", default=None, help="Jira user email to report on (default: yourself)")
def main(quarter, year, output_format, output, export_sheets, export_slides, export_xlsx, export_docx, export_pptx, detailed, llm_provider, llm_model, user):
    """Generate a quarterly review report."""
    try:
        config = get_config()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not quarter:
        quarter, default_year = _current_quarter()
    if not year:
        year = year or date.today().year

    start_date, end_date = _get_quarter_dates(quarter, year)
    client = JiraClient(config)

    console.print(f"[bold]Quarterly Report[/bold] — {quarter} {year} ({start_date} to {end_date})")
    console.print(f"Projects: {', '.join(config.active_projects)}")
    console.print()

    with console.status("Fetching quarterly data..."):
        report = quarterly_report(client, config, start_date, end_date, user=user)

    if detailed:
        text = format_quarterly_detailed(report, quarter, year)

        provider = llm_provider or config.llm_provider
        model = llm_model or config.llm_model
        if provider:
            console.print(f"[dim]Generating LLM narrative ({provider}/{model or 'default'})...[/dim]")
            from tools.llm.narrative import generate_narrative
            ai_text = generate_narrative(
                report, provider, model,
                ollama_base_url=config.ollama_base_url,
                openai_api_key=config.openai_api_key,
                anthropic_api_key=config.anthropic_api_key,
            )
            if ai_text:
                text = ai_text
            else:
                console.print("[yellow]LLM generation failed — using template report.[/yellow]")

        if output:
            with open(output, "w") as f:
                f.write(text)
            click.echo(f"Written to {output}")
        else:
            click.echo(text)

        if not any([export_sheets, export_slides, export_xlsx, export_docx, export_pptx]):
            return

    if not detailed and output_format == "json":
        data = {
            "quarter": f"{quarter} {year}",
            "date_range": report["date_range"],
            "total_closed": report["total_closed"],
            "by_project": report["by_project"],
            "by_type": report["by_type"],
            "by_label": report["by_label"],
            "issues": issues_to_dicts(report["issues"]),
        }
        text = json.dumps(data, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(text)
            click.echo(f"Written to {output}")
        else:
            click.echo(text)
        return

    if not detailed and output_format == "markdown":
        lines = [
            f"# Quarterly Report — {quarter} {year}",
            f"**Period:** {start_date} to {end_date}",
            f"**Projects:** {', '.join(config.active_projects)}",
            "",
            "## Summary",
            f"- **Total closed:** {report['total_closed']}",
            "",
            "## By Project",
        ]
        for proj, count in report["by_project"].items():
            lines.append(f"- {proj}: {count}")
        lines.append("")
        lines.append("## By Type")
        for itype, count in report["by_type"].items():
            lines.append(f"- {itype}: {count}")
        if report["by_label"]:
            lines.append("")
            lines.append("## Top Labels")
            for lbl, count in report["by_label"].items():
                lines.append(f"- {lbl}: {count}")
        lines.append("")
        lines.append("## Closed Issues")
        lines.append("| Key | Type | Summary | Closed |")
        lines.append("|-----|------|---------|--------|")
        for issue in report["issues"]:
            updated = issue.updated.strftime("%Y-%m-%d") if issue.updated else "?"
            lines.append(f"| {issue.key} | {issue.issue_type} | {issue.summary[:50]} | {updated} |")

        text = "\n".join(lines)
        if output:
            with open(output, "w") as f:
                f.write(text)
            click.echo(f"Written to {output}")
        else:
            click.echo(text)
        return

    # Table format (default — skip if --detailed already printed)
    if not detailed:
        console.print(f"[bold]Total closed:[/bold] {report['total_closed']}")
        console.print()

        if report["by_project"]:
            pt = Table(title="By Project")
            pt.add_column("Project", style="bold")
            pt.add_column("Closed", justify="right")
            for proj, count in report["by_project"].items():
                pt.add_row(proj, str(count))
            console.print(pt)
            console.print()

        if report["by_type"]:
            tt = Table(title="By Issue Type")
            tt.add_column("Type", style="bold")
            tt.add_column("Count", justify="right")
            for itype, count in report["by_type"].items():
                tt.add_row(itype, str(count))
            console.print(tt)
            console.print()

        if report["by_label"]:
            lt = Table(title="Top Labels")
            lt.add_column("Label", style="bold")
            lt.add_column("Count", justify="right")
            for lbl, count in report["by_label"].items():
                lt.add_row(lbl, str(count))
            console.print(lt)
            console.print()

        if report["issues"]:
            it = Table(title="Closed Issues")
            it.add_column("Key", style="bold")
            it.add_column("Project")
            it.add_column("Type")
            it.add_column("Summary")
            it.add_column("Closed")
            for issue in report["issues"]:
                updated = issue.updated.strftime("%Y-%m-%d") if issue.updated else "?"
                it.add_row(issue.key, issue.project_key, issue.issue_type, issue.summary[:50], updated)
            console.print(it)

    if export_sheets:
        try:
            from tools.export.sheets import export_quarterly_to_sheet
            url = export_quarterly_to_sheet(report, quarter, year)
            console.print(f"\n[green]Google Sheet:[/green] {url}")
        except ImportError:
            console.print("\n[red]Google export not set up. See Phase 5 setup instructions.[/red]")
        except Exception as e:
            console.print(f"\n[red]Sheet export failed: {e}[/red]")

    if export_slides:
        try:
            from tools.export.slides import create_quarterly_slides
            url = create_quarterly_slides(report, quarter, year)
            console.print(f"\n[green]Google Slides:[/green] {url}")
        except ImportError:
            console.print("\n[red]Google export not set up. See Phase 5 setup instructions.[/red]")
        except Exception as e:
            console.print(f"\n[red]Slides export failed: {e}[/red]")

    if export_xlsx:
        try:
            from tools.export.local import export_quarterly_xlsx
            path = export_quarterly_xlsx(report, quarter, year)
            console.print(f"\n[green]Excel file:[/green] {path}")
        except ImportError as e:
            console.print(f"\n[red]{e}[/red]")
        except Exception as e:
            console.print(f"\n[red]XLSX export failed: {e}[/red]")

    if export_docx:
        try:
            from tools.export.local import export_quarterly_docx
            path = export_quarterly_docx(report, quarter, year)
            console.print(f"\n[green]Word file:[/green] {path}")
        except ImportError as e:
            console.print(f"\n[red]{e}[/red]")
        except Exception as e:
            console.print(f"\n[red]DOCX export failed: {e}[/red]")

    if export_pptx:
        try:
            from tools.export.local import export_quarterly_pptx
            path = export_quarterly_pptx(report, quarter, year)
            console.print(f"\n[green]PowerPoint file:[/green] {path}")
        except ImportError as e:
            console.print(f"\n[red]{e}[/red]")
        except Exception as e:
            console.print(f"\n[red]PPTX export failed: {e}[/red]")


if __name__ == "__main__":
    main()
