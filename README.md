# KanbanZone CLI Skill for Claude Code, Codex & OpenClaw

Manage your [KanbanZone](https://kanbanzone.io) kanban boards — cards, columns, WIP limits, links, custom fields, and cross-board search — directly from your AI assistant or terminal. One self-contained Python script, zero dependencies beyond the standard library.

## Why This Exists

Small and mid-sized businesses run on kanban boards — tracking sales pipelines, client onboarding, marketing campaigns, hiring, operations, and more. But switching between your AI assistant and a browser to check the board, move cards, or create tasks breaks your flow.

This skill gives your AI assistant full access to your KanbanZone boards so it can check what's in progress, create and assign work items, enforce WIP limits, link cards to documents or resources, and search across all your boards — all through a simple conversation. Ask your AI assistant to "check the board," "what's blocked?", or "create a card for the Johnson proposal" and it just works.

## Key Features

- **Full board visibility** — see all your boards with at-a-glance metrics (active/blocked/overdue counts), view columns with WIP limits
- **Card management** — create, update, move, assign owners, add watchers, set priorities, flag blockers
- **Card links** — connect related cards to each other or link cards to external resources (documents, proposals, contracts, websites)
- **Custom fields** — track any metadata you need on cards (Client, Region, Value, Due Date, etc.)
- **WIP limit enforcement** — instantly see which columns are overloaded or starved, keeping work flowing smoothly
- **Cross-board search** — find any card by keyword, label, owner, or priority across all your boards
- **Filtering** — narrow down cards by column, label, owner, priority, blocked status, or keyword
- **Batch operations** — create multiple cards at once from a file
- **JSON output** — structured data for integration with other tools and automations
- **Zero dependencies** — single-file Python 3 script using only the standard library
- **Works everywhere** — compatible with Claude Code (Anthropic), OpenAI Codex, OpenClaw, or any CLI environment

## Quick Start

### 1. Get Your API Key

Go to [KanbanZone](https://kanbanzone.io) > **Settings** > **Organization Settings** > **Integrations** > **API Key**.

Direct link: `https://kanbanzone.io/settings/integrations`

### 2. Configure Environment

Create a `.env` file in the folder where you'll be working:

```bash
KANBANZONE_API_KEY=your-api-key-here
KANBANZONE_BOARD_ID=your-default-board-id
```

The script auto-loads `.env` from the current working directory — no shell export needed.

**Find column IDs:** Board Settings > API, or Organization Settings > Integrations > API.

### Working with Multiple Boards

If you use different boards for different areas of your business, create a `.env` file in each folder with the board ID for that area. The skill automatically picks up whichever `.env` is in your current working directory.

For example:

```
~/Marketing/.env      → KANBANZONE_BOARD_ID=marketing-board-id
~/Sales/.env          → KANBANZONE_BOARD_ID=sales-board-id
~/LegalDocuments/.env → KANBANZONE_BOARD_ID=legal-board-id
~/Operations/.env     → KANBANZONE_BOARD_ID=ops-board-id
```

When you open your AI assistant from `~/Marketing`, it automatically works with your marketing board. Open it from `~/Sales` and it works with your sales board. No configuration switching needed — just work from the right folder.

The `KANBANZONE_API_KEY` is the same across all boards, so you can either repeat it in each `.env` or set it once as a system environment variable and only put `KANBANZONE_BOARD_ID` in each folder's `.env`.

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
python3 scripts/kanbanzone_api.py create-card --title "Follow up with Johnson account" --column-id abc123

# Create a card with owner, watchers, and custom fields
python3 scripts/kanbanzone_api.py create-card --title "Prepare Q2 forecast" --column-id abc123 \
  --owner sarah@company.com --watcher cfo@company.com \
  --custom-field "Client=Acme Corp" --custom-field "Region=Northeast"

# Update a card
python3 scripts/kanbanzone_api.py update-card --id 42 --description "Updated scope and timeline"

# Flag a card as blocked
python3 scripts/kanbanzone_api.py update-card --id 42 --blocked true \
  --blocked-reason "Waiting on client approval"

# Move a card to a new column
python3 scripts/kanbanzone_api.py move-card --id 42 --column-id def456

# Assign an owner
python3 scripts/kanbanzone_api.py update-card --id 42 --owner sarah@company.com
```

### Card Links

```bash
# Link two related cards together
python3 scripts/kanbanzone_api.py link-card --id 42 --card 99

# Link a card to an external resource (contract, proposal, shared doc)
python3 scripts/kanbanzone_api.py link-card --id 42 \
  --url "https://docs.google.com/document/d/abc123" \
  --title "Client proposal" --type external

# Remove a card link
python3 scripts/kanbanzone_api.py unlink-card --id 42 --card 99

# Remove a URL link
python3 scripts/kanbanzone_api.py unlink-card --id 42 --url "https://..."
```

### Filtering & Search

```bash
# Filter cards on a board by label, owner, or status
python3 scripts/kanbanzone_api.py cards --label "Urgent" --owner "sarah@company.com" --blocked
python3 scripts/kanbanzone_api.py cards --column "In Progress" --priority 1
python3 scripts/kanbanzone_api.py cards --query "onboarding"

# Search cards across ALL boards
python3 scripts/kanbanzone_api.py search-cards --query "renewal" --label "Sales"
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
     "customFields": [{"label": "Region", "value": "West"}]}
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
| `Backlog` | Ideas and future work |
| `To Do` | Committed, ready to start |
| `Buffer` | Queue between stages |
| `In Progress` | Currently being worked on |
| `Done` | Completed |
| `Archive` | Historical items |

## What Your AI Assistant Can Do With This

Once this skill is installed, you can ask your AI assistant things like:

- "What's on our sales board right now?"
- "Show me everything that's blocked"
- "Create a card for the new client onboarding"
- "Move the Henderson proposal to Done"
- "Who owns the Q2 budget review?"
- "Are any columns over their WIP limit?"
- "Find all cards labeled Urgent across every board"
- "Link the vendor contract to card 47"

The assistant reads your boards, takes action, and reports back — no browser tab required.

## License

MIT
