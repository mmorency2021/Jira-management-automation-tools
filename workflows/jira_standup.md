# Jira Daily Standup

## Objective
Generate a daily standup report summarizing open issues, blockers, stale items, and recently closed work.

## When to Use
- Every morning before standup
- When asked "what's my status?" or "run my standup"
- Can be scheduled via cron for automated delivery

## Required Inputs
None — uses credentials from `~/.claude/.env.local` and project config from `.env`.

## Steps

1. **Run the standup CLI:**
   ```bash
   python3 -m tools.cli.standup
   ```

2. **Format options:**
   - Table (default): `--format table`
   - Markdown (for pasting into chat): `--format markdown`
   - JSON (for processing): `--format json`
   - Include watched projects: `--include-watched`
   - Override stale threshold: `--stale-days 7`
   - Write to file: `--output standup.md`

3. **Review the output** and flag any issues that need attention:
   - Stale items (not updated beyond threshold)
   - Blocked items
   - Items in progress for too long

## Scheduling (Claude Code users)
Set up a durable cron job for weekday mornings:
```
CronCreate("57 8 * * 1-5", "Run my daily Jira standup: python3 -m tools.cli.standup --format markdown", durable=true)
```
Note: Claude Code cron auto-expires after 7 days. Re-establish with "set up my daily standup cron".

## Expected Output
- Summary cards: total open, in progress, to do, stale, blocked, closed this week
- Active issues table with status, priority, last update
- Stale issues flagged with days since last update
- Blocked issues with blocker details
- Recently closed (last 7 days)

## Edge Cases
- If no issues found: likely a project filter issue. Check `JIRA_ACTIVE_PROJECTS` in `.env`.
- If API errors: check credentials in `~/.claude/.env.local`.
- Rate limiting: the client auto-retries with backoff.
