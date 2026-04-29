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
