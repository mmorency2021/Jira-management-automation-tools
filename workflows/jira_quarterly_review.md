# Jira Quarterly Review

## Objective
Generate end-of-quarter reports showing work completed, cycle times, and breakdowns by project/type/label. Export to various formats for sharing.

## When to Use
- End of quarter for reviews
- "Generate my Q1 review"
- "Export quarterly report to Excel"
- Manager requests for metrics

## Steps

1. **Generate the report:**
   ```bash
   jiraops quarterly --quarter Q1 --year 2026
   ```
   Defaults to the current quarter if not specified.

2. **Choose output format:**
   - Table (terminal): `--format table` (default)
   - Markdown: `--format markdown`
   - JSON: `--format json`
   - Write to file: `--output report.md`

3. **Export to files:**
   ```bash
   # Local files (no Google API needed)
   jiraops quarterly --export-xlsx
   jiraops quarterly --export-docx
   jiraops quarterly --export-pptx

   # Google Workspace (requires credentials.json setup)
   jiraops quarterly --export-sheets
   jiraops quarterly --export-slides
   ```

4. **Combine options:**
   ```bash
   jiraops quarterly --quarter Q1 --year 2026 --export-xlsx --export-pptx
   ```

## Report Contents
- **Total closed** issues in the quarter
- **Average cycle time** (created to resolved)
- **By project** breakdown
- **By issue type** (Bug, Task, Story, Epic)
- **Top labels** (up to 15)
- **Full issue list** with dates

## Local Export Formats
| Format | Library | Use Case |
|--------|---------|----------|
| .xlsx | openpyxl | Spreadsheet with multiple tabs (Summary, By Project, By Type, Issues, Labels) |
| .docx | python-docx | Formatted Word doc with tables, good for printing/sharing |
| .pptx | python-pptx | PowerPoint with summary slides and issue table |

## Google Export Setup
Only needed if you want to push directly to Google Workspace:
1. Create a Google Cloud project
2. Enable Sheets + Slides + Drive APIs
3. Create OAuth 2.0 Desktop credentials
4. Download `credentials.json` to project root
5. First run opens browser for OAuth consent

## Edge Cases
- Cycle time is approximate (created-to-updated, not created-to-resolved) since resolution date requires extra field.
- Large quarters (200+ issues) may take longer to fetch.
