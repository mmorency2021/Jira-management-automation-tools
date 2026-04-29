from __future__ import annotations

from .client import JiraClient
from .models import Issue


def my_open_issues(client: JiraClient, projects: list[str] = None) -> list[Issue]:
    jql = "assignee = currentUser() AND status NOT IN (Closed, Done)"
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY priority DESC, updated DESC"
    raw = client.search_issues(jql)
    return [Issue.from_raw(r) for r in raw]


def watched_issues(client: JiraClient, projects: list[str] = None) -> list[Issue]:
    jql = "watcher = currentUser() AND assignee != currentUser() AND status NOT IN (Closed, Done)"
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY updated DESC"
    raw = client.search_issues(jql, max_results=20)
    return [Issue.from_raw(r) for r in raw]


def recently_updated(
    client: JiraClient, projects: list[str] = None, days: int = 1
) -> list[Issue]:
    jql = f"assignee = currentUser() AND updated >= -{days}d"
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY updated DESC"
    raw = client.search_issues(jql)
    return [Issue.from_raw(r) for r in raw]


def stale_issues(
    client: JiraClient, projects: list[str] = None, days: int = 14
) -> list[Issue]:
    jql = f"assignee = currentUser() AND updated <= -{days}d AND status NOT IN (Closed, Done)"
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY updated ASC"
    raw = client.search_issues(jql)
    return [Issue.from_raw(r) for r in raw]


def recently_closed(
    client: JiraClient, projects: list[str] = None, days: int = 7
) -> list[Issue]:
    jql = f"assignee = currentUser() AND status IN (Closed, Done) AND updated >= -{days}d"
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY updated DESC"
    raw = client.search_issues(jql, max_results=20)
    return [Issue.from_raw(r) for r in raw]


def issues_by_status(client: JiraClient, project: str, status: str) -> list[Issue]:
    jql = f'project = {project} AND status = "{status}" AND assignee = currentUser()'
    jql += " ORDER BY updated DESC"
    raw = client.search_issues(jql)
    return [Issue.from_raw(r) for r in raw]


def blocked_issues(client: JiraClient, projects: list[str] = None) -> list[Issue]:
    jql = 'assignee = currentUser() AND status NOT IN (Closed, Done) AND issueFunction in linkedIssuesOf("status != Closed AND status != Done", "is blocked by")'
    if projects:
        project_list = ", ".join(projects)
        jql += f" AND project IN ({project_list})"
    jql += " ORDER BY priority DESC"
    try:
        raw = client.search_issues(jql)
        return [Issue.from_raw(r) for r in raw]
    except Exception:
        return _blocked_issues_fallback(client, projects)


def _blocked_issues_fallback(client: JiraClient, projects: list[str] = None) -> list[Issue]:
    """Fallback for instances without JQL functions — check issue links directly."""
    all_issues = my_open_issues(client, projects)
    blocked = []
    for issue in all_issues:
        for link in issue.links:
            if link.link_type.lower() in ("blocks", "depend") and link.direction == "inward":
                if link.linked_status_category.lower() not in ("done", "complete"):
                    blocked.append(issue)
                    break
    return blocked


def search(client: JiraClient, jql: str, max_results: int = 50) -> list[Issue]:
    raw = client.search_issues(jql, max_results=max_results)
    return [Issue.from_raw(r) for r in raw]


def quarterly_closed(
    client: JiraClient,
    projects: list[str],
    start_date: str,
    end_date: str,
) -> list[Issue]:
    project_list = ", ".join(projects)
    jql = (
        f"assignee = currentUser() AND project IN ({project_list}) "
        f'AND status IN (Closed, Done) AND resolved >= "{start_date}" '
        f'AND resolved <= "{end_date}" ORDER BY resolved DESC'
    )
    fields = [
        "summary", "status", "issuetype", "priority", "assignee",
        "reporter", "labels", "created", "updated", "description",
        "components", "parent", "resolutiondate",
    ]
    raw = client.search_issues(jql, fields=fields, max_results=200)
    return [Issue.from_raw(r) for r in raw]
