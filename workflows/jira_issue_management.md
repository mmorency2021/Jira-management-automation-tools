# Jira Issue Management

## Objective
Create, view, update, transition, comment on, and link Jira issues from the command line.

## When to Use
- "Show me issue NGC-588"
- "Move NGC-588 to done"
- "Create a task in NGC for..."
- "Add a comment to NGC-588"
- "Link NGC-588 to OCPBUGS-123"

## Command Reference

### View an issue
```bash
jiraops issues view NGC-588
```

### List my open issues
```bash
jiraops issues mine
jiraops issues mine --projects NGC,CNF
```

### Transition an issue
```bash
jiraops issues status NGC-588 "In Progress"
jiraops issues status NGC-588 Closed --comment "Done, verified in staging"
```

### Add a comment
```bash
jiraops issues comment NGC-588 "Tested and working"
```

### Create an issue
```bash
jiraops issues create --project NGC --summary "Fix deployment script" --type Task
jiraops issues create --project NGC --summary "Critical bug" --type Bug --priority High --assign user@redhat.com
```

### Update an issue
```bash
jiraops issues update NGC-588 --summary "New title"
jiraops issues update NGC-588 --assign user@redhat.com
jiraops issues update NGC-588 --add-label Q2-2026
jiraops issues update NGC-588 --remove-label old-label
```

### Link issues
```bash
jiraops issues link NGC-588 OCPBUGS-123 --type Blocks
jiraops issues link NGC-588 CNF-456 --type Related
```

## Conversational Mapping
| User says | Command |
|-----------|---------|
| "Show NGC-588" | `issues view NGC-588` |
| "What am I working on?" | `issues mine` |
| "Move NGC-588 to done" | `issues status NGC-588 Closed` |
| "Start working on NGC-588" | `issues status NGC-588 "In Progress"` |
| "Note on NGC-588: tested" | `issues comment NGC-588 "tested"` |
| "Create a bug in NGC" | `issues create --project NGC --type Bug --summary "..."` |

## Edge Cases
- Transition names vary by project workflow. The tool matches by name at runtime, not hardcoded IDs.
- If a transition fails, check available transitions with `issues status <key> <any-name>` — the error message lists valid options.
- Assignee uses email address format for Jira Cloud.
