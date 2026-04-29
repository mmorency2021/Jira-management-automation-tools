"""Export quarterly report to Google Slides."""
from __future__ import annotations

import uuid

from .auth import get_slides_service


def _rid() -> str:
    return str(uuid.uuid4()).replace("-", "")[:20]


def create_quarterly_slides(report: dict, quarter: str, year: int) -> str:
    service = get_slides_service()

    presentation = service.presentations().create(body={
        "title": f"Jira Quarterly Report — {quarter} {year}"
    }).execute()
    pres_id = presentation["presentationId"]

    requests = []

    # Title slide (already exists as slide 0)
    title_slide_id = presentation["slides"][0]["objectId"]
    title_elements = presentation["slides"][0]["pageElements"]
    for elem in title_elements:
        if elem.get("shape", {}).get("placeholder", {}).get("type") == "CENTERED_TITLE":
            requests.append({
                "insertText": {
                    "objectId": elem["objectId"],
                    "text": f"Quarterly Report\n{quarter} {year}",
                }
            })
        elif elem.get("shape", {}).get("placeholder", {}).get("type") == "SUBTITLE":
            requests.append({
                "insertText": {
                    "objectId": elem["objectId"],
                    "text": f"{report['date_range']['start']} to {report['date_range']['end']}",
                }
            })

    # Summary slide
    summary_slide_id = _rid()
    summary_body_id = _rid()
    requests.append({
        "createSlide": {
            "objectId": summary_slide_id,
            "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
            "placeholderIdMappings": [
                {"layoutPlaceholder": {"type": "TITLE"}, "objectId": _rid()},
                {"layoutPlaceholder": {"type": "BODY"}, "objectId": summary_body_id},
            ],
        }
    })

    # Project breakdown slide
    project_slide_id = _rid()
    project_body_id = _rid()
    requests.append({
        "createSlide": {
            "objectId": project_slide_id,
            "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
            "placeholderIdMappings": [
                {"layoutPlaceholder": {"type": "TITLE"}, "objectId": _rid()},
                {"layoutPlaceholder": {"type": "BODY"}, "objectId": project_body_id},
            ],
        }
    })

    # Execute slide creation first
    if requests:
        service.presentations().batchUpdate(
            presentationId=pres_id,
            body={"requests": requests}
        ).execute()

    # Now add text content
    text_requests = []

    # Summary text
    summary_text = (
        f"Total Issues Closed: {report['total_closed']}\n"
        f"Average Cycle Time: {report['avg_cycle_time_days']} days\n\n"
        f"By Type:\n"
    )
    for itype, count in report["by_type"].items():
        summary_text += f"  {itype}: {count}\n"

    text_requests.append({
        "insertText": {
            "objectId": summary_body_id,
            "text": summary_text,
        }
    })

    # Project breakdown text
    project_text = "Issues Closed by Project:\n\n"
    for proj, count in report["by_project"].items():
        project_text += f"  {proj}: {count}\n"

    if report["by_label"]:
        project_text += "\nTop Labels:\n"
        for lbl, count in list(report["by_label"].items())[:10]:
            project_text += f"  {lbl}: {count}\n"

    text_requests.append({
        "insertText": {
            "objectId": project_body_id,
            "text": project_text,
        }
    })

    if text_requests:
        service.presentations().batchUpdate(
            presentationId=pres_id,
            body={"requests": text_requests}
        ).execute()

    return f"https://docs.google.com/presentation/d/{pres_id}"
