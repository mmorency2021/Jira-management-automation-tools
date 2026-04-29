from __future__ import annotations

from . import queries
from .client import JiraClient
from .config import Config
from .models import Issue


def _resolve_projects(client: JiraClient, config: Config) -> list[str]:
    """Return active projects — auto-discovers from Jira if none configured."""
    if config.active_projects:
        return config.active_projects
    return queries.discover_projects(client)


def standup_report(client: JiraClient, config: Config) -> dict:
    projects = _resolve_projects(client, config)
    my_issues = queries.my_open_issues(client, projects)

    stale = [
        i for i in my_issues
        if i.days_since_update is not None
        and i.days_since_update >= config.stale_threshold_for_status(i.status)
    ]

    blocked = queries.blocked_issues(client, projects)

    closed = queries.recently_closed(client, projects, days=7)

    watched = []
    if config.watched_projects:
        watched = queries.watched_issues(client, config.watched_projects)

    by_status = {}
    for issue in my_issues:
        cat = issue.status_category
        by_status.setdefault(cat, []).append(issue)

    return {
        "my_issues": my_issues,
        "by_status": by_status,
        "stale": stale,
        "blocked": blocked,
        "recently_closed": closed,
        "watched": watched,
        "summary": {
            "total_open": len(my_issues),
            "in_progress": len(by_status.get("In Progress", [])),
            "to_do": len(by_status.get("To Do", [])),
            "stale_count": len(stale),
            "blocked_count": len(blocked),
            "closed_this_week": len(closed),
        },
    }


def dependency_report(client: JiraClient, config: Config) -> dict:
    projects = _resolve_projects(client, config)
    my_issues = queries.my_open_issues(client, projects)

    cross_project_deps = []
    for issue in my_issues:
        for link in issue.links:
            linked_project = link.linked_key.split("-")[0] if link.linked_key else ""
            if linked_project and linked_project != issue.project_key:
                cross_project_deps.append({
                    "issue": issue.key,
                    "issue_summary": issue.summary,
                    "link_type": link.link_type,
                    "direction": link.direction,
                    "linked_key": link.linked_key,
                    "linked_summary": link.linked_summary,
                    "linked_status": link.linked_status,
                    "linked_project": linked_project,
                    "at_risk": link.linked_status_category.lower() not in ("done", "complete"),
                })

    blocked = queries.blocked_issues(client, projects)

    return {
        "cross_project": cross_project_deps,
        "blocked": blocked,
        "my_issues": my_issues,
    }


def quarterly_report(
    client: JiraClient,
    config: Config,
    start_date: str,
    end_date: str,
) -> dict:
    projects = _resolve_projects(client, config)
    closed = queries.quarterly_closed(client, projects, start_date, end_date)

    by_project: dict[str, list[Issue]] = {}
    by_type: dict[str, list[Issue]] = {}
    by_label: dict[str, int] = {}

    for issue in closed:
        by_project.setdefault(issue.project_key, []).append(issue)
        by_type.setdefault(issue.issue_type, []).append(issue)
        for label in issue.labels:
            by_label[label] = by_label.get(label, 0) + 1

    total_cycle_days = 0
    cycle_count = 0
    for issue in closed:
        if issue.created and issue.updated:
            delta = issue.updated - issue.created
            total_cycle_days += delta.days
            cycle_count += 1

    avg_cycle_time = total_cycle_days / cycle_count if cycle_count else 0

    return {
        "date_range": {"start": start_date, "end": end_date},
        "total_closed": len(closed),
        "avg_cycle_time_days": round(avg_cycle_time, 1),
        "by_project": {k: len(v) for k, v in by_project.items()},
        "by_type": {k: len(v) for k, v in by_type.items()},
        "by_label": dict(sorted(by_label.items(), key=lambda x: x[1], reverse=True)[:15]),
        "issues": closed,
    }
