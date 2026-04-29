# JiraOps — Jira Automation Management Tools

A standalone Jira automation system for teams managing work across multiple projects. Daily standups, issue management, dependency tracking, bulk operations, quarterly reviews — from CLI, web dashboard, or Claude Code.

No MCP required. Works on macOS and Linux.

## Features

- **Daily Standup** — Automated standup reports with stale/blocked detection
- **Issue Management** — Create, view, update, transition, comment, and link issues
- **Cross-Project Dependencies** — Track blockers across project boundaries
- **Bulk Operations** — Batch update labels, priorities, statuses, assignments (with dry-run)
- **Quarterly Reviews** — Generate end-of-quarter reports with cycle time metrics
- **Multi-Format Export** — `.xlsx`, `.docx`, `.pptx` (local) or Google Sheets/Slides
- **Web Dashboard** — Browser-based UI at `localhost:5000`
- **Claude Code Integration** — Workflow SOPs for AI-assisted project management

## Quick Start

```bash
# Clone
git clone https://github.com/mmorency2021/Jira-management-automation-tools.git
cd Jira-management-automation-tools

# Setup (creates venv, installs deps, copies .env template)
bash setup.sh

# Configure
# 1. Get your API token: https://id.atlassian.com/manage-profile/security/api-tokens
# 2. Edit .env with your email, token, and project keys

# Activate venv
source venv/bin/activate

# Test
python -m tools.cli.standup
```

## Requirements

- Python 3.10+
- Jira Cloud instance with API token access

## CLI Reference

```bash
# Daily standup
python -m tools.cli.standup
python -m tools.cli.standup --format markdown --output standup.md
python -m tools.cli.standup --projects NGC,CNF --stale-days 7

# Issue management
python -m tools.cli.issues view NGC-588
python -m tools.cli.issues mine
python -m tools.cli.issues create --project NGC --summary "Fix deployment" --type Task
python -m tools.cli.issues status NGC-588 "In Progress"
python -m tools.cli.issues comment NGC-588 "Tested and working"
python -m tools.cli.issues update NGC-588 --add-label Q2-2026
python -m tools.cli.issues link NGC-588 OCPBUGS-123 --type Blocks

# Search
python -m tools.cli.search --project NGC --status "In Progress"
python -m tools.cli.search --jql "assignee = currentUser() AND labels = urgent"

# Dependencies
python -m tools.cli.deps
python -m tools.cli.deps --projects NGC,CNF --type Blocks

# Bulk operations (always preview first!)
python -m tools.cli.bulk label --jql "project=NGC AND updated >= -30d" --add-label Q2-2026 --dry-run
python -m tools.cli.bulk transition --jql "project=NGC AND status=Resolved" --status Closed --dry-run
python -m tools.cli.bulk assign --jql "project=NGC AND assignee is EMPTY" --assignee user@company.com --dry-run

# Quarterly review
python -m tools.cli.quarterly --quarter Q1 --year 2026
python -m tools.cli.quarterly --export-xlsx --export-pptx
python -m tools.cli.quarterly --export-sheets   # requires Google API setup
```

## Web Dashboard

```bash
python -m tools.web.app
# Open http://localhost:5000
```

Pages: Dashboard, Standup, Search, Issue Detail (with transition/comment forms), Quarterly Report.

## Configuration

All config goes in `.env` (copy from `.env.example`):

```ini
# Required
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token_here
JIRA_ACTIVE_PROJECTS=PROJ1,PROJ2

# Optional
JIRA_WATCHED_PROJECTS=PROJ3,PROJ4
JIRA_STALE_THRESHOLD_DAYS=14
JIRA_STALE_IN_PROGRESS_DAYS=7
JIRA_STALE_BLOCKED_DAYS=3
JIRA_STALE_REVIEW_DAYS=5
```

**Claude Code users:** Jira credentials can also live in `~/.claude/.env.local` (auto-detected).

## Export Formats

### Local (no setup needed)

- `--export-xlsx` — Excel workbook with Summary, By Project, By Type, Issues, Labels tabs
- `--export-docx` — Word document with formatted tables
- `--export-pptx` — PowerPoint with summary slides

### Google Workspace (optional)

1. Create a Google Cloud project
2. Enable Sheets + Slides + Drive APIs
3. Create OAuth 2.0 Desktop credentials
4. Download `credentials.json` to project root
5. Run `--export-sheets` or `--export-slides` (first run opens browser for consent)

## Architecture

```
tools/
  jira/           # Core library: config, HTTP client, models, queries, operations
  cli/            # CLI entry points: standup, issues, search, deps, bulk, quarterly
  web/            # Flask dashboard: routes, templates, static assets
  export/         # Google Workspace + local file export
workflows/        # Claude Code SOPs (markdown instructions for AI agent)
```

Built on the **WAT framework** (Workflows, Agents, Tools) — markdown SOPs drive AI orchestration, deterministic Python scripts handle execution.

## License

MIT
