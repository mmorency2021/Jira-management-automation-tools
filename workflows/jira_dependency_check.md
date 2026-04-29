# Jira Dependency Check

## Objective
Identify cross-project dependencies and blocked work across your projects.

## When to Use
- "What's blocking my work?"
- "Show cross-project dependencies"
- Before sprint planning to identify external blockers
- Risk assessment for project reviews

## Steps

1. **Run the dependency tracker:**
   ```bash
   python3 -m tools.cli.deps
   ```

2. **Filter by project:**
   ```bash
   python3 -m tools.cli.deps --projects NGC,CNF
   ```

3. **Filter by link type:**
   ```bash
   python3 -m tools.cli.deps --type Blocks
   ```

## Output
- **Cross-Project Dependencies** table: shows all issue links where the source and target are in different projects
- **At Risk** column: highlights dependencies where the target issue is not yet done
- **Blocked Issues** table: issues in your projects that are blocked by external work

## How It Works
The tool:
1. Fetches all your open issues across configured projects
2. Examines issue links for cross-project references
3. Identifies which dependencies are at risk (target not done)
4. Separately queries for blocked issues using JQL

## Edge Cases
- Requires `JIRA_ACTIVE_PROJECTS` to be set in `.env`
- Link types vary by Jira instance (Blocks, Depends, Related, etc.)
- If `issueFunction` JQL is not supported, falls back to link-based detection
