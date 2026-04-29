"""Flask web dashboard — visual interface for Jira automation."""
from __future__ import annotations

import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file

from tools.jira.client import JiraClient
from tools.jira.config import get_config
from tools.jira.formatters import format_quarterly_detailed, issues_to_dicts
from tools.jira import operations, queries
from tools.jira.reports import standup_report, quarterly_report


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())


def _client() -> JiraClient:
    return JiraClient(get_config())


def _config():
    return get_config()


@app.route("/")
def dashboard():
    config = _config()
    client = _client()
    report = standup_report(client, config)
    return render_template("dashboard.html", report=report, config=config)


@app.route("/standup")
def standup():
    config = _config()
    client = _client()
    report = standup_report(client, config)

    md_lines = []
    md_lines.append("## Daily Standup\n")
    for issue in report["my_issues"]:
        md_lines.append(f"- **{issue.key}** [{issue.status}] — {issue.summary}")
    if report["stale"]:
        md_lines.append("\n### Stale")
        for issue in report["stale"]:
            md_lines.append(f"- **{issue.key}** ({issue.days_since_update}d) — {issue.summary}")
    if report["blocked"]:
        md_lines.append("\n### Blocked")
        for issue in report["blocked"]:
            md_lines.append(f"- **{issue.key}** — {issue.summary}")
    if report["recently_closed"]:
        md_lines.append("\n### Recently Closed")
        for issue in report["recently_closed"]:
            md_lines.append(f"- **{issue.key}** — {issue.summary}")

    markdown_text = "\n".join(md_lines)
    return render_template("standup.html", report=report, markdown=markdown_text)


@app.route("/issues")
def issue_search():
    config = _config()
    client = _client()

    project = request.args.get("project", "")
    status = request.args.get("status", "")
    assignee = request.args.get("assignee", "")
    label = request.args.get("label", "")
    jql = request.args.get("jql", "")

    issues = []
    searched = False

    if jql:
        issues = queries.search(client, jql, max_results=50)
        searched = True
    elif any([project, status, assignee, label]):
        clauses = []
        if project:
            clauses.append(f"project = {project}")
        if status:
            clauses.append(f'status = "{status}"')
        if assignee:
            if assignee == "me":
                clauses.append("assignee = currentUser()")
            else:
                clauses.append(f'assignee = "{assignee}"')
        if label:
            clauses.append(f"labels = {label}")
        clauses.append("statusCategory != Done")
        query = " AND ".join(clauses) + " ORDER BY updated DESC"
        issues = queries.search(client, query, max_results=50)
        searched = True

    return render_template(
        "search.html",
        issues=issues,
        searched=searched,
        config=config,
        filters={"project": project, "status": status, "assignee": assignee, "label": label, "jql": jql},
    )


@app.route("/issues/<key>")
def issue_detail(key):
    client = _client()
    issue = operations.get_issue(client, key)
    transitions = operations.get_transitions(client, key)
    return render_template("issue.html", issue=issue, transitions=transitions)


@app.route("/issues/<key>/transition", methods=["POST"])
def issue_transition(key):
    client = _client()
    target = request.form.get("status", "")
    comment = request.form.get("comment", "").strip() or None
    try:
        operations.transition_issue(client, key, target, comment)
        flash(f"{key} transitioned to '{target}'", "success")
    except Exception as e:
        flash(f"Failed: {e}", "error")
    return redirect(url_for("issue_detail", key=key))


@app.route("/issues/<key>/comment", methods=["POST"])
def issue_comment(key):
    client = _client()
    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment cannot be empty", "error")
        return redirect(url_for("issue_detail", key=key))
    try:
        operations.add_comment(client, key, body)
        flash("Comment added", "success")
    except Exception as e:
        flash(f"Failed: {e}", "error")
    return redirect(url_for("issue_detail", key=key))


@app.route("/quarterly")
def quarterly():
    config = _config()
    client = _client()

    today = date.today()
    month = today.month
    if month <= 3:
        quarter, year = "Q1", today.year
    elif month <= 6:
        quarter, year = "Q2", today.year
    elif month <= 9:
        quarter, year = "Q3", today.year
    else:
        quarter, year = "Q4", today.year

    quarter = request.args.get("quarter", quarter)
    year = int(request.args.get("year", year))

    quarters = {"Q1": ("01-01", "03-31"), "Q2": ("04-01", "06-30"), "Q3": ("07-01", "09-30"), "Q4": ("10-01", "12-31")}
    start_md, end_md = quarters[quarter]
    start_date = f"{year}-{start_md}"
    end_date = f"{year}-{end_md}"

    report = quarterly_report(client, config, start_date, end_date)

    return render_template(
        "quarterly.html",
        report=report,
        quarter=quarter,
        year=year,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/quarterly/generate", methods=["POST"])
def quarterly_generate():
    config = _config()
    client = _client()

    quarter = request.form.get("quarter", "Q1")
    year = int(request.form.get("year", date.today().year))

    quarters_map = {"Q1": ("01-01", "03-31"), "Q2": ("04-01", "06-30"), "Q3": ("07-01", "09-30"), "Q4": ("10-01", "12-31")}
    start_md, end_md = quarters_map[quarter]
    start_date = f"{year}-{start_md}"
    end_date = f"{year}-{end_md}"

    report = quarterly_report(client, config, start_date, end_date)

    export_format = request.form.get("export_format", "")
    if export_format:
        return _handle_export(export_format, report, quarter, year)

    text = format_quarterly_detailed(report, quarter, year)

    llm_provider = request.form.get("llm_provider", "")
    llm_model = request.form.get("llm_model", "")
    llm_warning = None

    if llm_provider:
        from tools.llm.narrative import generate_narrative
        ai_text = generate_narrative(
            report, llm_provider, llm_model or config.llm_model,
            ollama_base_url=config.ollama_base_url,
            openai_api_key=config.openai_api_key,
            anthropic_api_key=config.anthropic_api_key,
        )
        if ai_text:
            text = ai_text
        else:
            llm_warning = f"LLM generation failed ({llm_provider}) — showing template report."

    return render_template(
        "quarterly.html",
        report=report,
        quarter=quarter,
        year=year,
        start_date=start_date,
        end_date=end_date,
        narrative=text,
        llm_warning=llm_warning,
        form_llm_provider=llm_provider,
        form_llm_model=llm_model,
    )


def _handle_export(fmt, report, quarter, year):
    import os
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        if fmt == "xlsx":
            from tools.export.local import export_quarterly_xlsx
            path = export_quarterly_xlsx(report, quarter, year, output_dir=tmp_dir)
            return send_file(path, as_attachment=True)
        elif fmt == "docx":
            from tools.export.local import export_quarterly_docx
            path = export_quarterly_docx(report, quarter, year, output_dir=tmp_dir)
            return send_file(path, as_attachment=True)
        elif fmt == "pptx":
            from tools.export.local import export_quarterly_pptx
            path = export_quarterly_pptx(report, quarter, year, output_dir=tmp_dir)
            return send_file(path, as_attachment=True)
    except ImportError as e:
        flash(f"Export package not installed: {e}", "error")
    except Exception as e:
        flash(f"Export failed: {e}", "error")

    return redirect(url_for("quarterly", quarter=quarter, year=year))


@app.route("/api/issues")
def api_issues():
    client = _client()
    jql = request.args.get("jql", "")
    if not jql:
        return jsonify({"error": "jql parameter required"}), 400
    issues = queries.search(client, jql, max_results=50)
    return jsonify(issues_to_dicts(issues))


def main():
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
