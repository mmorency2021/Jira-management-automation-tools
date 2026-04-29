"""Local file export — .xlsx and .docx for when Google API isn't available."""
from __future__ import annotations

from pathlib import Path


def export_quarterly_xlsx(report: dict, quarter: str, year: int, output_dir: str = ".") -> str:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise ImportError("openpyxl required for .xlsx export. Install with: pip install openpyxl")

    wb = Workbook()
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    def _write_header(ws, headers):
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill

    # Summary
    ws = wb.active
    ws.title = "Summary"
    _write_header(ws, ["Metric", "Value"])
    rows = [
        ["Quarter", f"{quarter} {year}"],
        ["Period", f"{report['date_range']['start']} to {report['date_range']['end']}"],
        ["Total Closed", report["total_closed"]],
        ["Avg Cycle Time (days)", report["avg_cycle_time_days"]],
    ]
    for i, row in enumerate(rows, 2):
        for j, val in enumerate(row, 1):
            ws.cell(row=i, column=j, value=val)

    # By Project
    ws_proj = wb.create_sheet("By Project")
    _write_header(ws_proj, ["Project", "Closed"])
    for i, (proj, count) in enumerate(report["by_project"].items(), 2):
        ws_proj.cell(row=i, column=1, value=proj)
        ws_proj.cell(row=i, column=2, value=count)

    # By Type
    ws_type = wb.create_sheet("By Type")
    _write_header(ws_type, ["Type", "Count"])
    for i, (itype, count) in enumerate(report["by_type"].items(), 2):
        ws_type.cell(row=i, column=1, value=itype)
        ws_type.cell(row=i, column=2, value=count)

    # Closed Issues
    ws_issues = wb.create_sheet("Closed Issues")
    _write_header(ws_issues, ["Key", "Project", "Type", "Priority", "Summary", "Labels", "Created", "Closed"])
    for i, issue in enumerate(report["issues"], 2):
        ws_issues.cell(row=i, column=1, value=issue.key)
        ws_issues.cell(row=i, column=2, value=issue.project_key)
        ws_issues.cell(row=i, column=3, value=issue.issue_type)
        ws_issues.cell(row=i, column=4, value=issue.priority)
        ws_issues.cell(row=i, column=5, value=issue.summary)
        ws_issues.cell(row=i, column=6, value=", ".join(issue.labels))
        ws_issues.cell(row=i, column=7, value=issue.created.strftime("%Y-%m-%d") if issue.created else "")
        ws_issues.cell(row=i, column=8, value=issue.updated.strftime("%Y-%m-%d") if issue.updated else "")

    # Labels
    if report["by_label"]:
        ws_labels = wb.create_sheet("By Label")
        _write_header(ws_labels, ["Label", "Count"])
        for i, (lbl, count) in enumerate(report["by_label"].items(), 2):
            ws_labels.cell(row=i, column=1, value=lbl)
            ws_labels.cell(row=i, column=2, value=count)

    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    filename = f"quarterly_report_{quarter}_{year}.xlsx"
    filepath = Path(output_dir) / filename
    wb.save(str(filepath))
    return str(filepath)


def export_quarterly_docx(report: dict, quarter: str, year: int, output_dir: str = ".") -> str:
    try:
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx required for .docx export. Install with: pip install python-docx")

    doc = Document()

    # Title
    title = doc.add_heading(f"Quarterly Report — {quarter} {year}", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        f"Period: {report['date_range']['start']} to {report['date_range']['end']}"
    ).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    # Summary
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(f"Total Issues Closed: {report['total_closed']}")
    doc.add_paragraph(f"Average Cycle Time: {report['avg_cycle_time_days']} days")

    # By Project
    doc.add_heading("By Project", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Project"
    hdr[1].text = "Closed"
    for proj, count in report["by_project"].items():
        row = table.add_row().cells
        row[0].text = proj
        row[1].text = str(count)

    doc.add_paragraph()

    # By Type
    doc.add_heading("By Issue Type", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Type"
    hdr[1].text = "Count"
    for itype, count in report["by_type"].items():
        row = table.add_row().cells
        row[0].text = itype
        row[1].text = str(count)

    doc.add_paragraph()

    # Top Labels
    if report["by_label"]:
        doc.add_heading("Top Labels", level=1)
        table = doc.add_table(rows=1, cols=2)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Label"
        hdr[1].text = "Count"
        for lbl, count in report["by_label"].items():
            row = table.add_row().cells
            row[0].text = lbl
            row[1].text = str(count)
        doc.add_paragraph()

    # Closed Issues
    doc.add_heading("Closed Issues", level=1)
    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Key"
    hdr[1].text = "Project"
    hdr[2].text = "Type"
    hdr[3].text = "Summary"
    hdr[4].text = "Closed"
    for issue in report["issues"]:
        row = table.add_row().cells
        row[0].text = issue.key
        row[1].text = issue.project_key
        row[2].text = issue.issue_type
        row[3].text = issue.summary[:60]
        row[4].text = issue.updated.strftime("%Y-%m-%d") if issue.updated else "?"

    filename = f"quarterly_report_{quarter}_{year}.docx"
    filepath = Path(output_dir) / filename
    doc.save(str(filepath))
    return str(filepath)


def export_quarterly_pptx(report: dict, quarter: str, year: int, output_dir: str = ".") -> str:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.enum.text import PP_ALIGN
    except ImportError:
        raise ImportError("python-pptx required for .pptx export. Install with: pip install python-pptx")

    prs = Presentation()

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Quarterly Report\n{quarter} {year}"
    slide.placeholders[1].text = f"{report['date_range']['start']} to {report['date_range']['end']}"

    # Summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Summary"
    body = slide.placeholders[1]
    tf = body.text_frame
    tf.text = f"Total Issues Closed: {report['total_closed']}"
    tf.add_paragraph().text = f"Average Cycle Time: {report['avg_cycle_time_days']} days"
    tf.add_paragraph().text = ""
    tf.add_paragraph().text = "By Issue Type:"
    for itype, count in report["by_type"].items():
        tf.add_paragraph().text = f"  {itype}: {count}"

    # By Project slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "By Project"
    body = slide.placeholders[1]
    tf = body.text_frame
    tf.text = "Issues Closed:"
    for proj, count in report["by_project"].items():
        tf.add_paragraph().text = f"  {proj}: {count}"

    if report["by_label"]:
        tf.add_paragraph().text = ""
        tf.add_paragraph().text = "Top Labels:"
        for lbl, count in list(report["by_label"].items())[:10]:
            tf.add_paragraph().text = f"  {lbl}: {count}"

    # Issues table slide
    if report["issues"]:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = "Closed Issues"

        issues = report["issues"][:20]
        rows = len(issues) + 1
        cols = 4
        table_shape = slide.shapes.add_table(rows, cols, Inches(0.5), Inches(1.5), Inches(9), Inches(5))
        table = table_shape.table

        headers = ["Key", "Project", "Type", "Summary"]
        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = h
            for p in cell.text_frame.paragraphs:
                p.font.bold = True
                p.font.size = Pt(10)

        for r, issue in enumerate(issues, 1):
            table.cell(r, 0).text = issue.key
            table.cell(r, 1).text = issue.project_key
            table.cell(r, 2).text = issue.issue_type
            table.cell(r, 3).text = issue.summary[:50]
            for c in range(cols):
                for p in table.cell(r, c).text_frame.paragraphs:
                    p.font.size = Pt(9)

    filename = f"quarterly_report_{quarter}_{year}.pptx"
    filepath = Path(output_dir) / filename
    prs.save(str(filepath))
    return str(filepath)
