from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _safe_get(data: dict, *keys, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _extract_adf_text(value) -> str:
    """Extract plain text from an ADF (Atlassian Document Format) document.

    API v3 returns description and comment bodies as ADF dicts, not strings.
    This recursively walks the ADF tree and concatenates all text nodes.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)

    parts = []
    for node in value.get("content", []):
        node_type = node.get("type", "")
        if node_type == "text":
            parts.append(node.get("text", ""))
        elif node_type in ("hardBreak",):
            parts.append("\n")
        elif "content" in node:
            parts.append(_extract_adf_text(node))

        if node_type in ("paragraph", "heading", "bulletList", "orderedList",
                         "listItem", "blockquote", "codeBlock", "rule"):
            parts.append("\n")

    return "".join(parts).strip()


@dataclass
class Comment:
    id: str
    body: str
    author_name: str
    created: datetime | None
    updated: datetime | None

    @classmethod
    def from_raw(cls, data: dict) -> Comment:
        return cls(
            id=str(data.get("id", "")),
            body=_extract_adf_text(data.get("body", "")),
            author_name=_safe_get(data, "author", "displayName", default="Unknown"),
            created=_parse_dt(data.get("created")),
            updated=_parse_dt(data.get("updated")),
        )


@dataclass
class IssueLink:
    link_type: str
    direction: str
    linked_key: str
    linked_summary: str
    linked_status: str
    linked_status_category: str

    @classmethod
    def from_raw(cls, data: dict) -> IssueLink:
        link_type = _safe_get(data, "type", "name", default="Related")

        if "outwardIssue" in data:
            direction = "outward"
            linked = data["outwardIssue"]
        elif "inwardIssue" in data:
            direction = "inward"
            linked = data["inwardIssue"]
        else:
            return cls(
                link_type=link_type, direction="unknown",
                linked_key="", linked_summary="", linked_status="",
                linked_status_category="",
            )

        return cls(
            link_type=link_type,
            direction=direction,
            linked_key=linked.get("key", ""),
            linked_summary=_safe_get(linked, "fields", "summary", default=""),
            linked_status=_safe_get(linked, "fields", "status", "name", default=""),
            linked_status_category=_safe_get(
                linked, "fields", "status", "statusCategory", "name", default=""
            ),
        )


@dataclass
class Issue:
    key: str
    id: str
    summary: str
    status: str
    status_category: str
    issue_type: str
    priority: str
    assignee_name: str
    assignee_email: str
    reporter_name: str
    labels: list[str]
    components: list[str]
    created: datetime | None
    updated: datetime | None
    description: str
    parent_key: str
    parent_summary: str
    comments: list[Comment] = field(default_factory=list)
    links: list[IssueLink] = field(default_factory=list)
    project_key: str = ""

    @property
    def days_since_update(self) -> int | None:
        if not self.updated:
            return None
        delta = datetime.now(self.updated.tzinfo) - self.updated
        return delta.days

    @property
    def is_done(self) -> bool:
        return self.status_category.lower() in ("done", "complete")

    @classmethod
    def from_raw(cls, data: dict) -> Issue:
        fields = data.get("fields", {})

        comments_data = _safe_get(fields, "comment", "comments", default=[])
        comments = [Comment.from_raw(c) for c in comments_data]

        links_data = fields.get("issuelinks", [])
        links = [IssueLink.from_raw(l) for l in links_data]

        components = [c.get("name", "") for c in fields.get("components", [])]

        return cls(
            key=data.get("key", ""),
            id=str(data.get("id", "")),
            summary=fields.get("summary", ""),
            status=_safe_get(fields, "status", "name", default="Unknown"),
            status_category=_safe_get(
                fields, "status", "statusCategory", "name", default="Unknown"
            ),
            issue_type=_safe_get(fields, "issuetype", "name", default="Unknown"),
            priority=_safe_get(fields, "priority", "name", default="Undefined"),
            assignee_name=_safe_get(fields, "assignee", "displayName", default="Unassigned"),
            assignee_email=_safe_get(fields, "assignee", "emailAddress", default=""),
            reporter_name=_safe_get(fields, "reporter", "displayName", default="Unknown"),
            labels=fields.get("labels", []),
            components=components,
            created=_parse_dt(fields.get("created")),
            updated=_parse_dt(fields.get("updated")),
            description=_extract_adf_text(fields.get("description")),
            parent_key=_safe_get(fields, "parent", "key", default=""),
            parent_summary=_safe_get(fields, "parent", "fields", "summary", default=""),
            comments=comments,
            links=links,
            project_key=_safe_get(fields, "project", "key", default=data.get("key", "").split("-")[0]),
        )


@dataclass
class Transition:
    id: str
    name: str

    @classmethod
    def from_raw(cls, data: dict) -> Transition:
        return cls(
            id=str(data.get("id", "")),
            name=_safe_get(data, "to", "name", default=data.get("name", "")),
        )


@dataclass
class Sprint:
    id: str
    name: str
    state: str
    start_date: datetime | None
    end_date: datetime | None
    goal: str

    @classmethod
    def from_raw(cls, data: dict) -> Sprint:
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            state=data.get("state", ""),
            start_date=_parse_dt(data.get("startDate")),
            end_date=_parse_dt(data.get("endDate")),
            goal=data.get("goal") or "",
        )
