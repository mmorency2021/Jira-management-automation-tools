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
jiraops standup
```

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Jira Cloud instance** with API access
- **Jira API Token** — Generate one at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
- **Your Jira email** — The email associated with your Atlassian account
- **Your Jira base URL** — e.g. `https://your-org.atlassian.net`

No Anthropic API key, Google Cloud credentials, or MCP setup required. Google export is optional.

## CLI Reference

```bash
# Daily standup
jiraops standup
jiraops standup --format markdown --output standup.md
jiraops standup --projects NGC,CNF --stale-days 7

# Issue management
jiraops issues view NGC-588
jiraops issues mine
jiraops issues create --project NGC --summary "Fix deployment" --type Task
jiraops issues status NGC-588 "In Progress"
jiraops issues comment NGC-588 "Tested and working"
jiraops issues update NGC-588 --add-label Q2-2026
jiraops issues link NGC-588 OCPBUGS-123 --type Blocks

# Search
jiraops search --project NGC --status "In Progress"
jiraops search --jql "assignee = currentUser() AND labels = urgent"

# Dependencies
jiraops deps
jiraops deps --projects NGC,CNF --type Blocks

# Bulk operations (always preview first!)
jiraops bulk label --jql "project=NGC AND updated >= -30d" --add-label Q2-2026 --dry-run
jiraops bulk transition --jql "project=NGC AND status=Resolved" --status Closed --dry-run
jiraops bulk assign --jql "project=NGC AND assignee is EMPTY" --assignee user@company.com --dry-run

# Quarterly review
jiraops quarterly --quarter Q1 --year 2026
jiraops quarterly --export-xlsx --export-pptx
jiraops quarterly --export-sheets   # requires Google API setup
```

## Web Dashboard

```bash
jiraops web
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

# Optional (auto-detected from your assigned issues if empty)
JIRA_ACTIVE_PROJECTS=
JIRA_WATCHED_PROJECTS=
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

## How It Works

### Solution Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER                                      │
│                                                                  │
│   "run my standup"    "show NGC-588"    "generate Q1 review"     │
└────────┬──────────────────┬──────────────────┬───────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Terminal   │    │  Web        │    │  Claude     │
│  CLI        │    │  Dashboard  │    │  Code       │
│             │    │  :5000      │    │  (reads     │
│  jiraops    │    │             │    │  workflow   │
│  standup    │    │  jiraops    │    │  SOPs then  │
│             │    │  web        │    │  runs CLI)  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │         CORE LIBRARY                  │
       │         tools/jira/                   │
       │                                       │
       │  .env ──► config.py                   │
       │              │                        │
       │              ▼                        │
       │         queries.py ── Build JQL       │
       │              │                        │
       │              ▼                        │
       │         client.py ── HTTP + Auth      │
       │           │  Retries, pagination,     │
       │           │  rate limit handling       │
       │           │                           │
       │           ▼                           │
       │    ┌─────────────┐                    │
       │    │  Jira REST  │                    │
       │    │  API v3     │                    │
       │    └──────┬──────┘                    │
       │           │                           │
       │           ▼                           │
       │     models.py ── Parse JSON → ADF     │
       │       → clean Python dataclasses      │
       │           │                           │
       │           ▼                           │
       │     reports.py ── Aggregate           │
       │       Group by status, detect stale,  │
       │       identify blockers, cycle times  │
       │           │                           │
       │           ▼                           │
       │     formatters.py ── Output           │
       │       Rich tables / Markdown / JSON   │
       └───────────┬──────────────────────────┘
                   │
                   ▼
       ┌──────────────────────────────────────┐
       │         EXPORT                        │
       │                                       │
       │  Local:   .xlsx  .docx  .pptx         │
       │  Google:  Sheets  Slides              │
       └──────────────────────────────────────┘
```

### Request Lifecycle

| Step | Component | What happens |
|------|-----------|-------------|
| 1 | **config.py** | Loads credentials from `.env`, auto-discovers projects if none configured |
| 2 | **queries.py** | Builds JQL query (e.g. `assignee = currentUser() AND status NOT IN (Closed, Done)`) |
| 3 | **client.py** | Sends HTTP request to Jira with Basic Auth, handles pagination and rate limits |
| 4 | **models.py** | Parses Jira's nested JSON + ADF documents into clean Python dataclasses |
| 5 | **reports.py** | Aggregates data: groups by status, flags stale/blocked, calculates cycle times |
| 6 | **formatters.py** | Renders output as Rich terminal tables, Markdown, or JSON |
| 7 | **export/** | Optionally exports to `.xlsx`, `.docx`, `.pptx`, Google Sheets, or Google Slides |

### Design Decisions

| Choice | Over | Reason |
|--------|------|--------|
| `requests` | `jira` library | 15+ fewer dependencies, installs on locked-down workstations |
| Flask | Streamlit | ~50 fewer packages, better fit for forms and action buttons |
| Dataclasses | Raw dicts | One place to parse Jira's nested JSON, all consumers get clean objects |
| Three interfaces | One | CLI works everywhere, web for browser users, Claude Code for AI-assisted |

### Directory Structure

```
tools/
  jira/           # Core library — shared by all interfaces
    config.py     #   Load and validate configuration
    client.py     #   HTTP client with auth, retries, pagination
    models.py     #   Dataclasses: Issue, Comment, Transition, Sprint
    queries.py    #   JQL builders and search operations
    operations.py #   Create, update, transition, comment, link
    reports.py    #   Standup, dependency, quarterly aggregation
    formatters.py #   Rich tables, markdown, JSON output
  cli/            # 6 CLI entry points (Click)
  web/            # Flask dashboard with templates
  export/         # Local files + Google Workspace
workflows/        # Claude Code SOPs (markdown)
```

## License

MIT
