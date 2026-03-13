# KanbanZone CLI Skill for Claude Code, Codex & OpenClaw

Manage [KanbanZone](https://kanbanzone.io) kanban boards — cards, columns, WIP limits, links, custom fields, and cross-board search — directly from your AI coding agent or terminal. One self-contained Python script, zero dependencies beyond the standard library.

## Why This Exists

Kanban boards are central to development workflows, but switching between your editor and a browser to check the board, move cards, or create tasks breaks flow. This skill brings the full KanbanZone API into your coding environment so your AI agent can check what's in progress, create and move cards, enforce WIP limits, link cards to commits or docs, and search across all boards — without leaving the terminal.

Combined with an AI coding agent, this enables powerful automation: the agent can read a card's description, do the work, update the card, move it to the next column, and link the commit — all in one session.

## Key Features

- **Full board visibility** — list boards with metrics (active/blocked/overdue counts), view columns with states and WIP limits
- **Card lifecycle management** — create, update, move, assign owners, add watchers, set priorities, flag blockers
- **Card links** — link cards to each other (related, blocked-by, etc.) or to external URLs (specs, PRs, docs)
- **Custom fields** — set and update arbitrary metadata on cards (Sprint, Team, Estimate, etc.)
- **WIP limit enforcement** — check current card counts against min/max WIP limits per column, flag violations
- **Cross-board search** — find cards by keyword, label, owner, or priority across all boards
- **Filtering** — filter cards by column, label, owner, priority, blocked status, or keyword
- **Batch operations** — create multiple cards at once from a JSON file
- **JSON output** — structured JSON for programmatic use by AI agents and scripts
- **Zero dependencies** — single-file Python 3 script using only the standard library (`urllib`, `json`, `argparse`, `base64`)
- **Works everywhere** — compatible with Claude Code (Anthropic), OpenAI Codex, OpenClaw, or any CLI environment

## Quick Start

### 1. Get Your API Key

Go to [KanbanZone](https://kanbanzone.io) > **Settings** > **Organization Settings** > **Integrations** > **API Key**.

Direct link: `https://kanbanzone.io/settings/integrations`

### 2. Configure Environment

Create a `.env` file in your project root (or export the variables):

```bash
KANBANZONE_API_KEY=your-api-key-here
KANBANZONE_BOARD_ID=your-default-board-id
```

The script auto-loads `.env` from the current working directory or the skill's parent directory — no shell export needed.

**Find column IDs:** Board Settings > API, or Organization Settings > Integrations > API.

### 3. List Your Boards

```bash
python3 scripts/kanbanzone_api.py boards
```

## Usage

### Board Overview

```bash
# List all boards with active/blocked/overdue metrics
python3 scripts/kanbanzone_api.py boards

# Get board details with columns, states, and WIP limits
python3 scripts/kanbanzone_api.py board --include-columns

# Check WIP limits — flags columns over max or under min
python3 scripts/kanbanzone_api.py wip-check
```

### Card Management

```bash
# List all cards on the default board
python3 scripts/kanbanzone_api.py cards

# Get a specific card by number
python3 scripts/kanbanzone_api.py card --number 42

# Create a card
python3 scripts/kanbanzone_api.py create-card --title "Implement login flow" --column-id abc123

# Create a card with owner, watchers, and custom fields
python3 scripts/kanbanzone_api.py create-card --title "Deploy v2.1" --column-id abc123 \
  --owner dev@example.com --watcher reviewer@example.com \
  --custom-field "Sprint=42" --custom-field "Team=Platform"

# Update a card
python3 scripts/kanbanzone_api.py update-card --id 42 --description "Updated requirements"

# Flag a card as blocked
python3 scripts/kanbanzone_api.py update-card --id 42 --blocked true \
  --blocked-reason "Waiting on API spec"

# Move a card to a new column
python3 scripts/kanbanzone_api.py move-card --id 42 --column-id def456

# Assign an owner
python3 scripts/kanbanzone_api.py update-card --id 42 --owner dev@example.com
```

### Card Links

```bash
# Link two cards together
python3 scripts/kanbanzone_api.py link-card --id 42 --card 99

# Link a card to an external URL (PR, doc, spec)
python3 scripts/kanbanzone_api.py link-card --id 42 --url "https://github.com/org/repo/pull/7" \
  --title "PR #7" --type external

# Remove a card link
python3 scripts/kanbanzone_api.py unlink-card --id 42 --card 99

# Remove a URL link
python3 scripts/kanbanzone_api.py unlink-card --id 42 --url "https://..."
```

### Filtering & Search

```bash
# Filter cards on a board by label, owner, status
python3 scripts/kanbanzone_api.py cards --label "Bug" --owner "dev@example.com" --blocked
python3 scripts/kanbanzone_api.py cards --column "In Progress" --priority 1
python3 scripts/kanbanzone_api.py cards --query "authentication"

# Search cards across ALL boards
python3 scripts/kanbanzone_api.py search-cards --query "deploy" --label "Enhancement"
```

### Batch Operations

Create multiple cards at once from a JSON file:

```bash
python3 scripts/kanbanzone_api.py create-cards --file cards.json
```

File format:
```json
{
  "board": "board-public-id",
  "cards": [
    {"title": "Card 1", "columnId": "col-id"},
    {"title": "Card 2", "columnId": "col-id", "watchers": ["a@b.com"],
     "customFields": [{"label": "Sprint", "value": "42"}]}
  ]
}
```

## Complete Command Reference

| Command | Description |
|---------|-------------|
| **Board** | |
| `boards` | List all boards with metrics (active/blocked/overdue) |
| `board` | Get a board's details (optionally include columns with `--include-columns`) |
| `wip-check` | Check WIP limits across all columns, flag violations |
| **Cards** | |
| `cards` | List cards with optional filters (`--label`, `--owner`, `--column`, `--priority`, `--blocked`, `--query`) |
| `card` | Get a single card by number |
| `create-card` | Create a card (supports `--owner`, `--watcher`, `--custom-field`, `--priority`) |
| `create-cards` | Batch create cards from a JSON file |
| `update-card` | Update card fields (description, owner, watchers, blocked status, custom fields) |
| `move-card` | Move a card to a different column |
| **Links** | |
| `link-card` | Add a card-to-card or external URL link |
| `unlink-card` | Remove a card-to-card or URL link |
| **Search** | |
| `search-cards` | Search cards by keyword across all boards |

All commands output JSON. Use `--board <id>` to override the default board from the environment.

## Column States

KanbanZone columns have a state that describes where cards are in the workflow:

| State | Meaning |
|-------|---------|
| `Backlog` | Pre-commitment items |
| `To Do` | Committed, ready to start |
| `Buffer` | Queue between stages |
| `In Progress` | Currently being worked on |
| `Done` | Completed |
| `Archive` | Historical items |

## Typical AI Agent Workflow

1. **Read the board** — `cards --column "To Do"` to find the next task
2. **Pick up a card** — `move-card` to "In Progress", `update-card` to assign owner
3. **Do the work** — the agent reads the card description, writes code, runs tests
4. **Link evidence** — `link-card --url` to attach the PR or commit
5. **Advance** — `move-card` to "Review" or "Done"
6. **Check flow** — `wip-check` to ensure no columns are overloaded

## License

MIT
