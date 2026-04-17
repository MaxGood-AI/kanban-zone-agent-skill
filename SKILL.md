---
name: kanban-zone
description: Interact with KanbanZone kanban boards via the KanbanZone API. Use when the user wants to manage kanban cards, view boards, move cards between columns, check WIP limits, link cards, search across boards, or get board-level metrics. Supports listing boards, creating/updating/moving cards, card links, custom fields, watchers, filtering, and cross-board search. Even if the user just says "check the board", "what's in progress", or mentions kanban cards, use this skill.
license: MIT
compatibility: Requires python3 and environment variables KANBANZONE_API_KEY and KANBANZONE_BOARD_ID
metadata:
  version: "2.1.0"
  openclaw:
    requires:
      env:
        - KANBANZONE_API_KEY
        - KANBANZONE_BOARD_ID
      bins:
        - python3
    primaryEnv: KANBANZONE_API_KEY
    homepage: https://docs.kanbanzone.io
---

# KanbanZone

Manage KanbanZone kanban boards through the KanbanZone Public API (v1.3).

## ⚠️ Exec Safety Rule — Multi-line Commands

**Never pass multi-line shell commands or long `--description` strings inline to `exec`.** The exec preflight will block them as "complex interpreter invocation".

**Always write to a temp file first:**

```python
# Write description to temp file
with open('/tmp/kz-desc.txt', 'w') as f:
    f.write("""Your multi-line
description here""")

# Then run the CLI via a script file
script = '''import subprocess
result = subprocess.run(
    ["python3", "skills/kanban-zone/scripts/kanbanzone_api.py",
     "update-card", "--id", "123",
     "--description", open("/tmp/kz-desc.txt").read()],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)
'''
with open('/tmp/kz-run.py', 'w') as f:
    f.write(script)
# Then exec: python3 /tmp/kz-run.py
```

Or simply build the whole call as a Python script in `/tmp/` and exec that file directly.

## Environment Setup

The CLI script reads two environment variables: `KANBANZONE_API_KEY` and `KANBANZONE_BOARD_ID`.

The script **automatically loads** these from a `.env` file if they are not already in the environment. It searches for `.env` in the current working directory and in the skill's parent directory. No shell export or command substitution is needed — just run the Python command directly.

**Get your API key:** Settings > Organization Settings > Integrations > API Key
Direct: `https://kanbanzone.io/settings/integrations`

**Find column IDs:** Board Settings > API, or Organization Settings > Integrations > API

## Quick Start

All examples below assume a `.env` file with `KANBANZONE_API_KEY` and `KANBANZONE_BOARD_ID` exists in the workspace root.

```bash
# List all boards
python3 scripts/kanbanzone_api.py boards

# Get board details with columns and WIP limits
python3 scripts/kanbanzone_api.py board --include-columns

# List cards on default board
python3 scripts/kanbanzone_api.py cards

# Filter cards by label and blocked status
python3 scripts/kanbanzone_api.py cards --label "Bug" --blocked

# Search cards by keyword
python3 scripts/kanbanzone_api.py cards --query "authentication"

# Get a specific card
python3 scripts/kanbanzone_api.py card --number 42

# Create a card with watchers and custom fields
python3 scripts/kanbanzone_api.py create-card --title "New task" --column-id abc123 \
  --owner user@example.com --watcher reviewer@example.com \
  --custom-field "Sprint=42" --custom-field "Team=Platform"

# Move a card to a column
python3 scripts/kanbanzone_api.py move-card --id 42 --column-id abc123

# Link cards together
python3 scripts/kanbanzone_api.py link-card --id 42 --card 99

# Link to an external URL
python3 scripts/kanbanzone_api.py link-card --id 42 --url "https://docs.example.com" --title "Spec"

# Remove a link
python3 scripts/kanbanzone_api.py unlink-card --id 42 --card 99

# Search cards across all boards
python3 scripts/kanbanzone_api.py search-cards --query "deploy"

# Check WIP limits
python3 scripts/kanbanzone_api.py wip-check
```

## Core Workflows

### Board Overview
1. Run `boards` to list all boards and their metrics (active/blocked/overdue counts).
2. Run `board --include-columns` on a specific board to see columns, their states, and WIP limits.
3. Use `wip-check` to compare current card counts against min/max WIP limits.

### Card Lifecycle
1. **Create**: `create-card --title "..." --column-id <backlog-col>` to add a card.
2. **Assign**: `update-card --id <num> --owner user@example.com` to assign an owner.
3. **Watch**: `update-card --id <num> --watcher watcher@example.com` to add watchers.
4. **Move**: `move-card --id <num> --column-id <target-col>` to advance through columns.
5. **Complete**: Move the card to a Done-state column.

### Card Review
1. `card --number <num>` to read card details, description, and current state.
2. `update-card --id <num> --description-file /tmp/kz_desc.txt` to update content (write file first, then run command).
3. `update-card --id <num> --blocked true --blocked-reason "Waiting on X"` to flag blockers.

### Description Updates (IMPORTANT)

**Always use `--description-file` instead of `--description` for creating or updating card descriptions.** This avoids multi-line quoting issues in shell commands.

**Always format descriptions as HTML, never Markdown.** KanbanZone renders card descriptions as HTML. Use tags like `<h3>`, `<p>`, `<ul>/<li>`, `<strong>`, `<em>`, `<a href="...">`, and `<br>` instead of Markdown syntax (`###`, `**`, `-`, `[text](url)`, etc.).

**⚠️ NEVER use HTML tables in descriptions.** KanbanZone **silently strips** `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, and `<td>` tags — the data disappears from the rendered card without warning. For **any** tabular data, use a `<pre>` block with fixed-width ASCII columns instead (this is the HTML equivalent of Markdown triple-backtick code blocks). Example:

```html
<pre>
Field         | Value
--------------+------------
Priority      | High
Due date      | 2026-04-30
Owner         | sarah@co.com
</pre>
```

Do not attempt to "illustrate tables of data with HTML tables" — always use `<pre>` with fixed-width characters.

Workflow:
1. Write the description content to a temp file (e.g., `/tmp/kz_desc.txt`) using the Write tool.
2. Run the command with `--description-file /tmp/kz_desc.txt`.

```bash
# CORRECT — use --description-file for all description changes
python3 scripts/kanbanzone_api.py update-card --id 42 --description-file /tmp/kz_desc.txt
python3 scripts/kanbanzone_api.py create-card --title "New task" --description-file /tmp/kz_desc.txt

# AVOID — inline --description with multi-line content
python3 scripts/kanbanzone_api.py update-card --id 42 --description "line 1\nline 2\n..."
```

The `--description-file` flag reads the entire file content as the description. It overrides `--description` if both are provided.

### Card Links
1. `link-card --id <num> --card <other-num>` to create a card-to-card link (default type: `related`).
2. `link-card --id <num> --url "https://..." --title "Reference" --type external` to add an external URL link.
3. `unlink-card --id <num> --card <other-num>` to remove a card link.
4. `unlink-card --id <num> --url "https://..."` to remove a URL link.

### Custom Fields
Set custom metadata on cards during creation or update:
```bash
python3 scripts/kanbanzone_api.py create-card --title "Task" \
  --custom-field "Sprint=42" --custom-field "Team=Platform" --custom-field "Estimate=3d"
```

### Filtering & Search
Filter cards on a single board:
```bash
python3 scripts/kanbanzone_api.py cards --label "Bug" --owner "dev@example.com" --blocked
python3 scripts/kanbanzone_api.py cards --column "In Progress" --priority 1
python3 scripts/kanbanzone_api.py cards --query "login"
```

Search across all boards:
```bash
python3 scripts/kanbanzone_api.py search-cards --query "deploy" --label "Enhancement"
```

### WIP Limit Checking
Run `wip-check` to get a report comparing current card counts to each column's min/max WIP limits. Columns exceeding their max or below their min are flagged.

### Batch Operations
`create-cards --file cards.json` to create multiple cards at once. The JSON file should contain:
```json
{
  "board": "board-public-id",
  "cards": [
    {"title": "Card 1", "columnId": "col-id"},
    {"title": "Card 2", "columnId": "col-id", "watchers": ["a@b.com"], "customFields": [{"label": "Sprint", "value": "42"}]}
  ]
}
```

## Board & Column Name Resolution (Agent Cache)

To avoid unnecessary API calls when resolving board or column names to IDs, maintain a local cache file in your memory directory.

### Cache file

Store `kanbanzone-cache.json` in your persistent memory directory with this structure:

```json
{
  "boards": {
    "<board-public-id>": {
      "name": "Board Name",
      "columns": {
        "<column-id>": { "name": "Column Name", "state": "In Progress" }
      }
    }
  },
  "updated": "2026-02-25T12:00:00Z"
}
```

### Lookup flow

1. **Before** calling the API to resolve a board name to an ID or a column name to an ID, read `kanbanzone-cache.json` from your memory directory.
2. If the cache file exists and contains a matching name (case-insensitive), use the cached ID directly — **do not call the API**.
3. If the cache file is missing, or the name is not found, call the appropriate API command (`boards` or `board --include-columns`) and then **update the cache file** with the full response data before proceeding.

### Auto-populate

Whenever you run `boards` or `board --include-columns` for any reason, always update `kanbanzone-cache.json` with the returned data. This keeps the cache fresh as a side effect of normal operations.

### Cache refresh

If the user says board or column data is stale, or explicitly asks to refresh the cache, re-fetch from the API (`boards` then `board --include-columns` for each board) and overwrite `kanbanzone-cache.json`.

### Important notes

- The cache lives in **your agent memory directory**, not in the skill's directory. This keeps the skill stateless and portable.
- Column IDs change if a board is restructured — always honor a cache miss by falling back to the API.
- When writing the cache, set `"updated"` to the current ISO 8601 timestamp.

## Column States

| State | Meaning |
|-------|---------|
| `Backlog` | Pre-commitment items |
| `To Do` | Committed, ready to start |
| `Buffer` | Queue between stages |
| `In Progress` | Currently being worked on |
| `Done` | Completed |
| `Archive` | Historical items |
| `None` | No state assigned |

## Script Reference

All commands output JSON. Run `python3 scripts/kanbanzone_api.py --help` for full usage.

| Command | Description |
|---------|-------------|
| `boards` | List all boards with metrics |
| `board` | Get a specific board's details |
| `cards` | List cards (paginated, with optional filters) |
| `card` | Get a single card by number |
| `create-card` | Create one card (supports watchers, custom fields) |
| `create-cards` | Create multiple cards from JSON |
| `update-card` | Update card fields (supports watchers, custom fields) |
| `move-card` | Move card to a column |
| `link-card` | Add a card-to-card or URL link |
| `unlink-card` | Remove a card-to-card or URL link |
| `search-cards` | Search cards across all boards |
| `wip-check` | Check WIP limits across columns |

## API Reference

See [references/api-reference.md](./references/api-reference.md) for complete endpoint documentation, data models, and response schemas.
