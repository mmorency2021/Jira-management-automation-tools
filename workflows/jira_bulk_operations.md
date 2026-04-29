# Jira Bulk Operations

## Objective
Perform batch updates on multiple Jira issues — transitions, labels, assignments, priorities.

## When to Use
- "Label all NGC issues from this month with Q2-2026"
- "Close all resolved issues in NGC"
- "Assign all unassigned CNF bugs to me"
- End-of-sprint cleanup

## Safety Rules
1. **Always `--dry-run` first** — preview what will change before executing
2. **Maximum 50 issues** per batch
3. **Interactive confirmation** required unless `--confirm` is passed
4. **Never run bulk operations without reviewing the preview**

## Commands

### Bulk transition
```bash
# Preview
python3 -m tools.cli.bulk transition --jql "project=NGC AND status=Resolved" --status Closed --dry-run

# Execute
python3 -m tools.cli.bulk transition --jql "project=NGC AND status=Resolved" --status Closed --confirm
```

### Bulk label
```bash
# Add label
python3 -m tools.cli.bulk label --jql "project=NGC AND updated >= -30d" --add-label Q2-2026 --dry-run

# Remove label
python3 -m tools.cli.bulk label --jql "project=NGC" --remove-label old-label --dry-run

# Both at once
python3 -m tools.cli.bulk label --jql "..." --add-label new --remove-label old --dry-run
```

### Bulk assign
```bash
python3 -m tools.cli.bulk assign --jql "project=NGC AND assignee is EMPTY AND type=Bug" --assignee user@redhat.com --dry-run
```

### Bulk priority
```bash
python3 -m tools.cli.bulk priority --jql "project=NGC AND labels=critical" --priority High --dry-run
```

## Workflow for Claude
When a user asks for bulk operations:
1. Construct the JQL based on their request
2. Run with `--dry-run` first and show the preview
3. Ask the user to confirm before executing
4. Run without `--dry-run` and with `--confirm`

## Edge Cases
- Some transitions require specific fields (e.g., resolution). The tool will report individual failures.
- Failed operations on individual issues don't stop the batch — it continues and reports the error count at the end.
