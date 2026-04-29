from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Issue


STATUS_COLORS = {
    "In Progress": "yellow",
    "To Do": "blue",
    "New": "blue",
    "Refinement": "cyan",
    "Review": "magenta",
    "Closed": "green",
    "Done": "green",
    "ASSIGNED": "yellow",
    "Resolved": "green",
}


def _status_style(status: str) -> str:
    return STATUS_COLORS.get(status, "white")


def _days_ago(dt: datetime | None) -> str:
    if not dt:
        return "?"
    delta = datetime.now(dt.tzinfo) - dt
    days = delta.days
    if days == 0:
        return "today"
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


def format_standup_table(
    issues: list[Issue],
    title: str = "My Active Issues",
    show_project: bool = True,
) -> Table:
    table = Table(title=title, show_lines=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    if show_project:
        table.add_column("Project", style="dim")
    table.add_column("Type", style="dim")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Summary", max_width=60)
    table.add_column("Updated", style="dim")

    for issue in issues:
        status_text = Text(issue.status, style=_status_style(issue.status))
        row = [issue.key]
        if show_project:
            row.append(issue.project_key)
        row.extend([
            issue.issue_type,
            status_text,
            issue.priority,
            issue.summary[:60],
            _days_ago(issue.updated),
        ])
        table.add_row(*row)

    return table


def format_stale_table(issues: list[Issue], threshold: int) -> Table:
    table = Table(title=f"Stale Issues (>{threshold} days)", show_lines=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Project", style="dim")
    table.add_column("Status")
    table.add_column("Days Stale", justify="right")
    table.add_column("Summary", max_width=50)

    for issue in sorted(issues, key=lambda i: i.days_since_update or 0, reverse=True):
        days = issue.days_since_update or 0
        severity = "red bold" if days > threshold * 2 else "yellow" if days > threshold else "white"
        table.add_row(
            issue.key,
            issue.project_key,
            Text(issue.status, style=_status_style(issue.status)),
            Text(str(days), style=severity),
            issue.summary[:50],
        )

    return table


def format_blocked_table(issues: list[Issue]) -> Table:
    table = Table(title="Blocked Issues", show_lines=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Summary", max_width=40)
    table.add_column("Blocked By", style="red")
    table.add_column("Blocker Status")

    for issue in issues:
        blockers = [
            l for l in issue.links
            if l.link_type.lower() in ("blocks", "depend")
            and l.direction == "inward"
            and l.linked_status_category.lower() not in ("done", "complete")
        ]
        for blocker in blockers:
            table.add_row(
                issue.key,
                issue.summary[:40],
                blocker.linked_key,
                Text(blocker.linked_status, style=_status_style(blocker.linked_status)),
            )

    return table


def format_issue_detail(issue: Issue) -> Panel:
    lines = [
        f"[bold]{issue.key}[/bold] — {issue.summary}",
        "",
        f"  Status:   [{_status_style(issue.status)}]{issue.status}[/]",
        f"  Type:     {issue.issue_type}",
        f"  Priority: {issue.priority}",
        f"  Assignee: {issue.assignee_name}",
        f"  Reporter: {issue.reporter_name}",
        f"  Project:  {issue.project_key}",
        f"  Labels:   {', '.join(issue.labels) if issue.labels else 'none'}",
        f"  Created:  {_days_ago(issue.created)}",
        f"  Updated:  {_days_ago(issue.updated)}",
    ]

    if issue.parent_key:
        lines.append(f"  Parent:   {issue.parent_key} — {issue.parent_summary}")

    if issue.links:
        lines.append("")
        lines.append("  [bold]Links:[/bold]")
        for link in issue.links:
            lines.append(f"    {link.link_type} ({link.direction}) → {link.linked_key} [{link.linked_status}]")

    if issue.comments:
        lines.append("")
        lines.append(f"  [bold]Recent Comments ({len(issue.comments)}):[/bold]")
        for comment in issue.comments[-3:]:
            lines.append(f"    {comment.author_name} ({_days_ago(comment.created)}):")
            body_preview = comment.body[:100].replace("\n", " ")
            lines.append(f"      {body_preview}")

    return Panel("\n".join(lines), title=issue.key, border_style="cyan")


def format_markdown_standup(
    my_issues: list[Issue],
    stale: list[Issue],
    blocked: list[Issue],
    recently_closed_list: list[Issue],
    watched: list[Issue] = None,
) -> str:
    lines = ["# Daily Standup", ""]

    in_progress = [i for i in my_issues if i.status_category.lower() == "in progress"]
    todo = [i for i in my_issues if i.status_category.lower() == "to do"]
    in_review = [i for i in my_issues if "review" in i.status.lower()]
    other = [i for i in my_issues if i not in in_progress + todo + in_review]

    if in_progress:
        lines.append("## In Progress")
        for issue in in_progress:
            lines.append(f"- **{issue.key}** — {issue.summary} (updated {_days_ago(issue.updated)})")
        lines.append("")

    if in_review:
        lines.append("## In Review")
        for issue in in_review:
            lines.append(f"- **{issue.key}** — {issue.summary}")
        lines.append("")

    if todo:
        lines.append("## To Do")
        for issue in todo:
            lines.append(f"- **{issue.key}** — {issue.summary}")
        lines.append("")

    if other:
        lines.append("## Other")
        for issue in other:
            lines.append(f"- **{issue.key}** [{issue.status}] — {issue.summary}")
        lines.append("")

    if blocked:
        lines.append("## Blocked")
        for issue in blocked:
            blockers = [l for l in issue.links if l.link_type.lower() in ("blocks", "depend") and l.direction == "inward"]
            blocker_text = ", ".join(f"{b.linked_key} ({b.linked_status})" for b in blockers)
            lines.append(f"- **{issue.key}** — blocked by {blocker_text}")
        lines.append("")

    if stale:
        lines.append("## Stale (needs attention)")
        for issue in stale:
            lines.append(f"- **{issue.key}** — {issue.summary} ({issue.days_since_update} days)")
        lines.append("")

    if recently_closed_list:
        lines.append("## Recently Closed")
        for issue in recently_closed_list:
            lines.append(f"- **{issue.key}** — {issue.summary}")
        lines.append("")

    if watched:
        lines.append("## Watched Issues (other teams)")
        for issue in watched:
            lines.append(f"- **{issue.key}** [{issue.status}] — {issue.summary}")
        lines.append("")

    return "\n".join(lines)


def _accomplishment_bullet(issue: Issue) -> str:
    """Format a single issue as an accomplishment bullet point."""
    desc = ""
    if issue.description:
        clean = issue.description.replace("\n", " ").strip()
        if len(clean) > 200:
            clean = clean[:200] + "..."
        desc = f": {clean}"
    cycle = ""
    if issue.created and issue.updated:
        days = (issue.updated - issue.created).days
        cycle = f" *(resolved in {days} day{'s' if days != 1 else ''})*"
    return f"- **{issue.key}** [{issue.issue_type}] {issue.summary}{desc}{cycle}"


def format_quarterly_detailed(report: dict, quarter: str, year: int) -> str:
    """Generate a detailed narrative quarterly report in markdown."""
    start = report["date_range"]["start"]
    end = report["date_range"]["end"]
    total = report["total_closed"]
    avg_cycle = report["avg_cycle_time_days"]
    fastest = report.get("fastest_cycle_days", 0)
    slowest = report.get("slowest_cycle_days", 0)
    by_project = report["by_project"]
    by_type = report["by_type"]
    by_priority = report.get("by_priority", {})
    by_component = report.get("by_component", {})
    by_label = report.get("by_label", {})
    by_epic = report.get("by_epic", {})
    standalone = report.get("standalone", [])
    issues = report["issues"]

    high_impact = [i for i in issues if i.priority in ("Blocker", "Critical", "Urgent", "Highest")]
    bugs_fixed = by_type.get("Bug", 0)
    fast_turnaround = [
        i for i in issues
        if i.created and i.updated and (i.updated - i.created).days <= 2
    ]
    cross_project_links = set()
    for issue in issues:
        for link in issue.links:
            linked_proj = link.linked_key.split("-")[0] if link.linked_key else ""
            if linked_proj and linked_proj != issue.project_key:
                cross_project_links.add(linked_proj)

    lines = []

    # --- Title ---
    lines.append(f"# Quarterly Report — {quarter} {year}")
    lines.append(f"**Period:** {start} to {end}")
    lines.append("")

    # --- Summary Paragraph ---
    lines.append("## Summary")
    lines.append("")

    project_names = ", ".join(sorted(by_project.keys()))
    summary_parts = [
        f"During {quarter} {year}, **{total} issues** were successfully resolved across "
        f"**{len(by_project)} project{'s' if len(by_project) != 1 else ''}** "
        f"({project_names}), with an average cycle time of **{avg_cycle} days**."
    ]

    if by_type:
        type_parts = [f"{count} {name.lower()}{'s' if count != 1 else ''}" for name, count in
                      sorted(by_type.items(), key=lambda x: x[1], reverse=True)]
        summary_parts.append(f"The work delivered includes {', '.join(type_parts)}.")

    if by_epic:
        summary_parts.append(
            f"Contributions spanned **{len(by_epic)} epic{'s' if len(by_epic) != 1 else ''}/"
            f"initiative{'s' if len(by_epic) != 1 else ''}**, reflecting focused execution on strategic objectives."
        )

    if high_impact:
        summary_parts.append(
            f"**{len(high_impact)} high-priority item{'s' if len(high_impact) != 1 else ''}** "
            f"(Blocker/Critical/Urgent) {'were' if len(high_impact) != 1 else 'was'} resolved, "
            f"keeping critical paths unblocked."
        )

    if bugs_fixed:
        summary_parts.append(
            f"**{bugs_fixed} bug{'s' if bugs_fixed != 1 else ''}** were identified and fixed, "
            f"improving system stability and reliability."
        )

    if fast_turnaround:
        summary_parts.append(
            f"**{len(fast_turnaround)} issue{'s' if len(fast_turnaround) != 1 else ''}** "
            f"{'were' if len(fast_turnaround) != 1 else 'was'} resolved within 2 days, "
            f"demonstrating strong responsiveness to urgent needs."
        )

    if cross_project_links:
        summary_parts.append(
            f"Cross-project coordination was maintained with "
            f"{', '.join(sorted(cross_project_links))}."
        )

    lines.append(" ".join(summary_parts))
    lines.append("")

    # --- Key Metrics ---
    lines.append("## Key Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Issues resolved | {total} |")
    lines.append(f"| Projects touched | {len(by_project)} |")
    lines.append(f"| Avg cycle time | {avg_cycle} days |")
    lines.append(f"| Fastest resolution | {fastest} day{'s' if fastest != 1 else ''} |")
    lines.append(f"| Slowest resolution | {slowest} days |")
    if by_epic:
        lines.append(f"| Epics/initiatives | {len(by_epic)} |")
    if high_impact:
        lines.append(f"| High-priority resolved | {len(high_impact)} |")
    if fast_turnaround:
        lines.append(f"| Resolved within 2 days | {len(fast_turnaround)} |")
    lines.append("")

    # --- Accomplishments by Epic ---
    if by_epic:
        lines.append("## Accomplishments by Initiative")
        lines.append("")

        for epic_key, epic_data in sorted(by_epic.items(), key=lambda x: len(x[1]["issues"]), reverse=True):
            epic_issues = epic_data["issues"]
            lines.append(f"### {epic_key} — {epic_data['summary']}")
            lines.append("")
            lines.append(
                f"Completed **{len(epic_issues)} item{'s' if len(epic_issues) != 1 else ''}** "
                f"under this initiative:"
            )
            lines.append("")
            for issue in epic_issues:
                lines.append(_accomplishment_bullet(issue))
            lines.append("")

    # --- Accomplishments (standalone, by project) ---
    if standalone:
        header = "Accomplishments by Project" if not by_epic else "Additional Accomplishments"
        lines.append(f"## {header}")
        lines.append("")

        standalone_by_project: dict[str, list] = {}
        for issue in standalone:
            standalone_by_project.setdefault(issue.project_key, []).append(issue)

        for proj, proj_issues in sorted(standalone_by_project.items()):
            lines.append(f"### {proj}")
            lines.append("")
            for issue in proj_issues:
                lines.append(_accomplishment_bullet(issue))
            lines.append("")

    # --- Breakdowns ---
    if len(by_project) > 1:
        lines.append("## Breakdown by Project")
        lines.append("")
        for proj, count in sorted(by_project.items(), key=lambda x: x[1], reverse=True):
            pct = round(count / total * 100) if total else 0
            lines.append(f"- **{proj}**: {count} issues ({pct}%)")
        lines.append("")

    lines.append("## Breakdown by Type")
    lines.append("")
    for itype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / total * 100) if total else 0
        lines.append(f"- **{itype}**: {count} ({pct}%)")
    lines.append("")

    if by_priority:
        lines.append("## Breakdown by Priority")
        lines.append("")
        for prio, count in by_priority.items():
            lines.append(f"- **{prio}**: {count}")
        lines.append("")

    if by_component:
        lines.append("## Components Impacted")
        lines.append("")
        for comp, count in by_component.items():
            lines.append(f"- **{comp}**: {count} issues")
        lines.append("")

    if by_label:
        lines.append("## Top Labels")
        lines.append("")
        for lbl, count in by_label.items():
            lines.append(f"- `{lbl}`: {count}")
        lines.append("")

    # --- Highlights ---
    if high_impact:
        lines.append("## High-Priority Items Resolved")
        lines.append("")
        for issue in high_impact:
            lines.append(f"- **{issue.key}** [{issue.priority}] {issue.summary}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated by JiraOps — {quarter} {year}*")
    lines.append("")

    return "\n".join(lines)


def report_to_prompt_data(report: dict) -> str:
    """Serialize quarterly report data into readable text for an LLM prompt."""
    lines = []
    dr = report["date_range"]
    lines.append(f"QUARTERLY REPORT DATA — {dr['start']} to {dr['end']}")
    lines.append(f"Total issues resolved: {report['total_closed']}")
    lines.append(f"Average cycle time: {report['avg_cycle_time_days']} days")
    lines.append(f"Fastest resolution: {report.get('fastest_cycle_days', 0)} days")
    lines.append(f"Slowest resolution: {report.get('slowest_cycle_days', 0)} days")
    lines.append("")

    if report.get("by_project"):
        lines.append("BY PROJECT:")
        for proj, count in report["by_project"].items():
            lines.append(f"  {proj}: {count} issues")
        lines.append("")

    if report.get("by_type"):
        lines.append("BY TYPE:")
        for itype, count in report["by_type"].items():
            lines.append(f"  {itype}: {count}")
        lines.append("")

    if report.get("by_priority"):
        lines.append("BY PRIORITY:")
        for prio, count in report["by_priority"].items():
            lines.append(f"  {prio}: {count}")
        lines.append("")

    if report.get("by_component"):
        lines.append("COMPONENTS:")
        for comp, count in report["by_component"].items():
            lines.append(f"  {comp}: {count}")
        lines.append("")

    by_epic = report.get("by_epic", {})
    if by_epic:
        lines.append("ISSUES BY EPIC/INITIATIVE:")
        for epic_key, epic_data in by_epic.items():
            lines.append(f"\n  Epic: {epic_key} — {epic_data['summary']}")
            for issue in epic_data["issues"]:
                cycle = ""
                if issue.created and issue.updated:
                    cycle = f" (cycle: {(issue.updated - issue.created).days} days)"
                desc = ""
                if issue.description:
                    clean = issue.description.replace("\n", " ").strip()[:150]
                    desc = f" | {clean}"
                lines.append(
                    f"    - {issue.key} [{issue.issue_type}] [{issue.priority}] "
                    f"{issue.summary}{cycle}{desc}"
                )

    standalone = report.get("standalone", [])
    if standalone:
        lines.append("\nSTANDALONE ISSUES (no epic):")
        for issue in standalone:
            cycle = ""
            if issue.created and issue.updated:
                cycle = f" (cycle: {(issue.updated - issue.created).days} days)"
            desc = ""
            if issue.description:
                clean = issue.description.replace("\n", " ").strip()[:150]
                desc = f" | {clean}"
            lines.append(
                f"  - {issue.key} [{issue.issue_type}] [{issue.priority}] "
                f"{issue.summary}{cycle}{desc}"
            )

    return "\n".join(lines)


def issues_to_dicts(issues: list[Issue]) -> list[dict]:
    return [
        {
            "key": i.key,
            "project": i.project_key,
            "summary": i.summary,
            "status": i.status,
            "type": i.issue_type,
            "priority": i.priority,
            "assignee": i.assignee_name,
            "labels": ", ".join(i.labels),
            "created": i.created.isoformat() if i.created else "",
            "updated": i.updated.isoformat() if i.updated else "",
            "days_since_update": i.days_since_update,
        }
        for i in issues
    ]
