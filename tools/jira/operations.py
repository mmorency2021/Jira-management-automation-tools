"""Write operations against the Jira API — create, update, transition, comment, link."""
from __future__ import annotations

from .client import JiraClient
from .models import Comment, Issue, Transition


def _text_to_adf(text: str) -> dict:
    """Convert plain text to Atlassian Document Format (ADF).

    API v3 requires ADF for description and comment bodies.
    """
    paragraphs = text.split("\n\n") if "\n\n" in text else [text]
    content = []
    for para in paragraphs:
        if para.strip():
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": para.strip()}],
            })
    return {"version": 1, "type": "doc", "content": content or [
        {"type": "paragraph", "content": [{"type": "text", "text": ""}]}
    ]}


def _resolve_assignee(client: JiraClient, identifier: str) -> dict:
    """Resolve an email or display name to an accountId for Jira Cloud."""
    if identifier.startswith("accountid:"):
        return {"accountId": identifier[10:]}
    try:
        users = client.get("user/search", params={"query": identifier, "maxResults": 1})
        if users:
            return {"accountId": users[0]["accountId"]}
    except Exception:
        pass
    return {"accountId": identifier}


def get_issue(client: JiraClient, key: str) -> Issue:
    data = client.get(f"issue/{key}", params={
        "fields": "summary,status,issuetype,priority,assignee,reporter,"
                  "labels,created,updated,description,issuelinks,parent,"
                  "components,comment",
    })
    return Issue.from_raw(data)


def get_transitions(client: JiraClient, key: str) -> list[Transition]:
    data = client.get(f"issue/{key}/transitions")
    return [Transition.from_raw(t) for t in data.get("transitions", [])]


def transition_issue(
    client: JiraClient,
    key: str,
    target_status: str,
    comment: str = None,
) -> Issue:
    transitions = get_transitions(client, key)
    target_lower = target_status.lower()

    match = None
    for t in transitions:
        if t.name.lower() == target_lower:
            match = t
            break
    if not match:
        for t in transitions:
            if target_lower in t.name.lower():
                match = t
                break

    if not match:
        available = ", ".join(f"'{t.name}'" for t in transitions)
        raise ValueError(
            f"No transition to '{target_status}' available for {key}. "
            f"Available: {available}"
        )

    payload: dict = {"transition": {"id": match.id}}
    if comment:
        payload["update"] = {
            "comment": [{"add": {"body": _text_to_adf(comment)}}]
        }

    client.post(f"issue/{key}/transitions", json=payload)
    return get_issue(client, key)


def update_issue(client: JiraClient, key: str, fields: dict) -> Issue:
    update_fields = {}

    if "assignee" in fields:
        assignee = fields.pop("assignee")
        update_fields["assignee"] = _resolve_assignee(client, str(assignee))

    if "priority" in fields:
        priority = fields.pop("priority")
        update_fields["priority"] = {"name": priority}

    if "labels" in fields:
        update_fields["labels"] = fields.pop("labels")

    update_fields.update(fields)

    client.put(f"issue/{key}", json={"fields": update_fields})
    return get_issue(client, key)


def add_labels(client: JiraClient, key: str, labels: list[str]) -> Issue:
    current = get_issue(client, key)
    merged = list(set(current.labels + labels))
    client.put(f"issue/{key}", json={"fields": {"labels": merged}})
    return get_issue(client, key)


def remove_labels(client: JiraClient, key: str, labels: list[str]) -> Issue:
    current = get_issue(client, key)
    remaining = [l for l in current.labels if l not in labels]
    client.put(f"issue/{key}", json={"fields": {"labels": remaining}})
    return get_issue(client, key)


def add_comment(client: JiraClient, key: str, body: str) -> Comment:
    data = client.post(f"issue/{key}/comment", json={"body": _text_to_adf(body)})
    return Comment.from_raw(data)


def create_issue(
    client: JiraClient,
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str = None,
    assignee: str = None,
    labels: list[str] = None,
    parent_key: str = None,
    priority: str = None,
) -> Issue:
    fields: dict = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = _text_to_adf(description)
    if assignee:
        fields["assignee"] = _resolve_assignee(client, assignee)
    if labels:
        fields["labels"] = labels
    if parent_key:
        fields["parent"] = {"key": parent_key}
    if priority:
        fields["priority"] = {"name": priority}

    data = client.post("issue", json={"fields": fields})
    return get_issue(client, data["key"])


def link_issues(
    client: JiraClient,
    from_key: str,
    to_key: str,
    link_type: str = "Related",
) -> None:
    client.post("issueLink", json={
        "type": {"name": link_type},
        "inwardIssue": {"key": from_key},
        "outwardIssue": {"key": to_key},
    })


def delete_issue(client: JiraClient, key: str) -> None:
    client.delete(f"issue/{key}")
