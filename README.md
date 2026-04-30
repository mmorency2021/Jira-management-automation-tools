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
- **Email Reports** — Send standup and quarterly reports by email via local Postfix or SMTP relay
- **Built-in Scheduler** — Automatic daily standup and quarterly email delivery
- **Team Visibility** — `--user` flag to view any team member's tickets as a manager
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

### LLM-Enhanced Reports (optional)

The `--detailed` flag generates a structured quarterly report. Add an LLM provider for richer narrative analysis that highlights achievements, identifies themes, and writes an executive-ready summary.

#### Ollama (free, local)

```bash
# Install Ollama: https://ollama.ai
ollama pull llama3
# In .env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

#### OpenAI

```bash
pip install openai
# In .env:
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

#### Anthropic

```bash
pip install anthropic
# In .env:
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

You can also pass the provider per-command without changing `.env`:

```bash
jiraops quarterly --detailed --llm ollama --model llama3
```

If no LLM is configured, `--detailed` still produces the template-based report.

### Email Reports (optional)

JiraOps can email standup and quarterly reports automatically using your system's built-in SMTP server (Postfix). No external email services or API keys required.

#### Setup

**macOS** (Postfix is pre-installed):

```bash
sudo postfix start
```

**Linux (Debian/Ubuntu)**:

```bash
sudo apt install postfix    # select "Local only" or "Internet Site"
sudo systemctl start postfix
```

**Linux (RHEL/Fedora)**:

```bash
sudo dnf install postfix
sudo systemctl start postfix
```

Then configure the recipient in `.env`:

```ini
JIRAOPS_EMAIL_RECIPIENT=your.email@company.com
```

That's it. The default config sends via `localhost:25` with no authentication.

#### Optional: Gmail or Corporate SMTP

If you prefer sending through an authenticated relay:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=your_app_password
JIRAOPS_EMAIL_RECIPIENT=your.email@company.com
```

#### Sending Reports

```bash
# Send standup report now
jiraops mail-standup

# Preview without sending
jiraops mail-standup --dry-run

# Send quarterly report
jiraops mail-quarterly --quarter Q1 --year 2026

# With LLM narrative
jiraops mail-quarterly --llm ollama --model llama3

# Override recipient
jiraops mail-standup --to someone@company.com
```

#### Automatic Scheduler

The built-in scheduler sends reports on a schedule:

```bash
# Install scheduler dependency
pip install schedule

# Start the scheduler daemon
jiraops scheduler

# Custom standup time
jiraops scheduler --standup-time 08:30

# Disable specific reports
jiraops scheduler --no-quarterly
```

The scheduler sends:
- **Daily standup** at the configured time (default: 09:00)
- **Quarterly report** on a specific day of quarter-end months (default: 1st of March, June, September, December)

Configure via `.env`:

```ini
JIRAOPS_SCHEDULER_STANDUP_TIME=09:00
JIRAOPS_SCHEDULER_QUARTERLY_DAY=1
```

To run in the background:

```bash
# Using nohup
nohup jiraops scheduler &

# Or with systemd (Linux)
# Create a service file for persistent operation
```

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
  cli/            # CLI entry points (Click) — standup, issues, search, deps, bulk, quarterly, mail, scheduler
  web/            # Flask dashboard with templates
  mail/           # SMTP email sender (smtplib)
  llm/            # LLM provider integration (Ollama, OpenAI, Anthropic)
  export/         # Local files + Google Workspace
workflows/        # Claude Code SOPs (markdown)
```

## License

MIT
