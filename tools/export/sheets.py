"""Export quarterly report to Google Sheets."""
from __future__ import annotations

from .auth import get_gspread_client


def export_quarterly_to_sheet(report: dict, quarter: str, year: int) -> str:
    gc = get_gspread_client()

    title = f"Jira Quarterly Report — {quarter} {year}"
    sh = gc.create(title)

    # Summary sheet
    ws = sh.sheet1
    ws.update_title("Summary")
    ws.update("A1", [
        ["Metric", "Value"],
        ["Quarter", f"{quarter} {year}"],
        ["Period", f"{report['date_range']['start']} to {report['date_range']['end']}"],
        ["Total Closed", report["total_closed"]],
        ["Avg Cycle Time (days)", report["avg_cycle_time_days"]],
    ])
    ws.format("A1:B1", {"textFormat": {"bold": True}})

    # By Project sheet
    ws_proj = sh.add_worksheet(title="By Project", rows=20, cols=5)
    rows = [["Project", "Closed"]]
    for proj, count in report["by_project"].items():
        rows.append([proj, count])
    ws_proj.update("A1", rows)
    ws_proj.format("A1:B1", {"textFormat": {"bold": True}})

    # By Type sheet
    ws_type = sh.add_worksheet(title="By Type", rows=20, cols=5)
    rows = [["Type", "Count"]]
    for itype, count in report["by_type"].items():
        rows.append([itype, count])
    ws_type.update("A1", rows)
    ws_type.format("A1:B1", {"textFormat": {"bold": True}})

    # Issues sheet
    ws_issues = sh.add_worksheet(title="Closed Issues", rows=250, cols=10)
    rows = [["Key", "Project", "Type", "Priority", "Summary", "Labels", "Created", "Closed"]]
    for issue in report["issues"]:
        rows.append([
            issue.key,
            issue.project_key,
            issue.issue_type,
            issue.priority,
            issue.summary,
            ", ".join(issue.labels),
            issue.created.strftime("%Y-%m-%d") if issue.created else "",
            issue.updated.strftime("%Y-%m-%d") if issue.updated else "",
        ])
    ws_issues.update("A1", rows)
    ws_issues.format("A1:H1", {"textFormat": {"bold": True}})

    # Labels sheet
    if report["by_label"]:
        ws_labels = sh.add_worksheet(title="By Label", rows=30, cols=5)
        rows = [["Label", "Count"]]
        for lbl, count in report["by_label"].items():
            rows.append([lbl, count])
        ws_labels.update("A1", rows)
        ws_labels.format("A1:B1", {"textFormat": {"bold": True}})

    return sh.url
