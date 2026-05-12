# Kanban Zone Skill for Claude Code

## What It Is

Manage your [Kanban Zone](https://kanbanzone.com) boards — cards, columns, comments, checklists, tasks, webhooks, and flow reports — directly from any Claude Code-compatible workspace. Built in official partnership with Kanban Zone, this skill wraps the **Kanban Zone Public API v1.4** using nothing but the Python 3 standard library: no virtual environment, no third-party packages, and no external runtime dependencies of any kind. Drop it into a repo, point it at your API key, and your AI assistant gains full board access in seconds.

## Install

```bash
# Clone the skill into your project's skills/ directory (or anywhere on your path)
git clone https://github.com/MaxGoodWork/kanban-zone skills/kanban-zone

# If you use Claude Code's plugin system:
claude plugin add skills/kanban-zone
```

**Requirements:** Python 3.8 or later (verify with `python3 --version`).

Create a `.env` file in the directory where you'll be working:

```bash
KANBAN_ZONE_API_KEY=your-api-key-here
KANBAN_ZONE_BOARD_ID=your-default-board-public-id
```

The skill loads `.env` automatically — no shell export needed. `KANBAN_ZONE_BOARD_ID` sets the default board for every command; pass `--board <id>` to override it for a single call.

**Multiple boards:** create one `.env` per project folder, each with the relevant `KANBAN_ZONE_BOARD_ID`. The same `KANBAN_ZONE_API_KEY` works across all boards and can be set once as a system environment variable if you prefer.

## API Key

1. Log in to Kanban Zone and go to **Settings → Organization Settings → Integrations → API Key**.
   Direct link: <https://kanbanzone.io/settings/integrations>
2. Click **Generate** (or copy an existing key).
3. Paste the raw key into your `.env` as `KANBAN_ZONE_API_KEY=...`. The CLI base64-encodes it automatically before every request — do not pre-encode it yourself.

## Cookbook

Each example below is a complete, copy-pasteable bash command. All examples use the grouped v3 command surface (`boards list`, `cards create`, etc.).

### 1. List boards and pick one to work on

Inspect all your boards at a glance before deciding which one to target for the session.

```bash
python3 scripts/kanban_zone_api.py boards list --include-columns
```

Pick the `publicId` from the output and drop it into your `.env` as `KANBAN_ZONE_BOARD_ID`, or pass `--board <id>` inline for a one-off override.

### 2. Create a card with watchers and custom fields

Create a fully annotated card in the "Backlog" column, assign it, add a watcher, and stamp two custom fields.

```bash
python3 scripts/kanban_zone_api.py cards create \
  --title "Q3 client proposal — Acme Corp" \
  --column-id COL_ABC123 \
  --owner sarah@company.com \
  --watcher cfo@company.com \
  --priority 1 --label "Sales" --size M --due "09/30/2026" \
  --custom-field "Client=Acme Corp" \
  --custom-field "Region=Northeast"
```

### 3. Update a description from a temp file

Long HTML descriptions clash with shell quoting. Write the body to a temp file first, then hand it to the CLI via `--description-file`.

```bash
python3 -c "
import textwrap
open('/tmp/desc.txt', 'w').write(textwrap.dedent('''
  <h3>Scope</h3>
  <p>Revised timeline following client call on 2026-05-09.</p>
  <ul>
    <li>Phase 1 due 2026-06-01</li>
    <li>Phase 2 due 2026-07-15</li>
  </ul>
''').strip())
"
python3 scripts/kanban_zone_api.py cards update --id 42 \
  --description-file /tmp/desc.txt
```

Note: Kanban Zone renders descriptions as HTML. Use `<pre>` blocks for any tabular data — `<table>` tags are silently stripped by the platform.

### 4. Move a card to "In Progress"

Provide the target column ID (visible in Board Settings → API).

```bash
python3 scripts/kanban_zone_api.py cards move --id 42 --column-id COL_INPROG
```

### 5. Add a comment to a card

Post a status update or question directly on the card's activity feed.

```bash
python3 scripts/kanban_zone_api.py comments add --card 42 \
  --text "Scope confirmed with client. Proceeding to design phase."
```

### 6. Create a checklist with tasks; mark one complete

Add a QA checklist to a card, then immediately mark the first task done.

```bash
# Create the checklist (returns the checklist ID and first task ID)
python3 scripts/kanban_zone_api.py checklists create --card 42 \
  --title "QA Sign-off" \
  --task "Smoke test on staging" \
  --task "Cross-browser check" \
  --task "Accessibility audit"

# Mark task 1001 complete (replace with the returned task ID)
python3 scripts/kanban_zone_api.py tasks update --id 1001 --completed true
```

### 7. Register a webhook and verify a delivery's signature

Subscribe to card-created events, then use the built-in HMAC verifier to confirm the first delivery is authentic.

```bash
# Register the webhook
python3 scripts/kanban_zone_api.py webhooks create \
  --url "https://hooks.yourapp.com/kanban" \
  --event card.created \
  --secret "your-shared-secret"

# After the first delivery arrives, verify its signature
python3 scripts/kanban_zone_api.py webhooks verify-signature \
  --payload-file /tmp/webhook-body.json \
  --signature "sha256=<value-from-X-KZ-Signature-header>" \
  --secret "your-shared-secret"
```

### 8. Pull a throughput report for the last quarter

Measure how many cards were completed between two dates.

```bash
python3 scripts/kanban_zone_api.py reports throughput \
  --from-date 2026-01-01 --to-date 2026-03-31
```

Other available report types: `arrival-rate`, `cycle-time`, `lead-time`, `flow`, `flow-efficiency`, `allocation`, `abandoned-effort`.

### 9. Audit overdue cards across all boards

Search the whole organisation for cards marked overdue, regardless of which board they live on.

```bash
python3 scripts/kanban_zone_api.py cards search \
  --query "" --overdue --include-archived
```

Pipe the JSON output to `jq '.[] | {id, title, board}' ` for a quick triage list.

### 10. Bulk-create cards from a JSON file

Create dozens of cards in one shot from a structured file — ideal for sprint planning or importing a backlog.

```bash
# cards.json format:
# {
#   "board": "BOARD_PUBLIC_ID",
#   "cards": [
#     {"title": "Card 1", "columnId": "COL_ID"},
#     {"title": "Card 2", "columnId": "COL_ID",
#      "watchers": ["a@b.com"],
#      "customFields": [{"label": "Region", "value": "West"}]}
#   ]
# }
python3 scripts/kanban_zone_api.py cards create-bulk --file cards.json
```

## Command Reference

The full command surface — every group, every subcommand, every flag — is documented in [`SKILL.md`](SKILL.md). The canonical authoritative list of groups and subcommands is the `GROUPS_AND_SUBCOMMANDS` dict in [`tests/test_cli_help.py`](tests/test_cli_help.py); that dict is the contract the test suite enforces.

**Groups at a glance:** `boards`, `cards`, `comments`, `checklists`, `tasks`, `webhooks`, `reports`, `tokens`, `org`.

All commands output JSON and accept `--board <id>` to override the default board.

## What's New in v3

- **API v1.4 coverage** — comments, checklists, tasks, tokens, webhooks, and eight flow-metric report types, all missing from v2.
- **Grouped CLI** — nine resource groups (`boards`, `cards`, `comments`, …) replace the flat monolithic surface, making discovery and tab-completion practical.
- **Hidden legacy aliases** — every v2 flat command (`create-card`, `move-card`, etc.) still works as a hidden alias so existing scripts need no changes.
- **Bidirectional ID cache** — card numbers and IDs resolve symmetrically; the cache is invalidated automatically when tracked files change.
- **Silent endpoint migration** — deprecated API endpoints redirect transparently; no consumer code changes required.
- **Signature verifier** — `webhooks verify-signature` provides HMAC-SHA256 delivery verification with a single command.
- **≥ 95 % test coverage** — enforced as a hard quality gate; `make coverage` reports the current figure.

Full history: see [`CHANGELOG.md`](CHANGELOG.md).

## Migration from v2

Every v2 flat command (`create-card`, `update-card`, `move-card`, `link-card`, `search-cards`, etc.) is registered as a hidden alias in v3 — it does not appear in `--help` but it still works. Existing scripts and saved AI prompts that use those names require zero changes. New code should use the grouped surface (`cards create`, `cards move`, `cards links-add`, `cards search`). For the complete alias-to-grouped-command mapping, see [`references/migration-from-v2.md`](references/migration-from-v2.md).

## License

MIT — see [`LICENSE.txt`](LICENSE.txt).

## Acknowledgements

This skill is built in official partnership with [Kanban Zone](https://kanbanzone.com). Kanban Zone provides the Public API (v1.4) that powers every command, and the partnership ensures the skill stays current as the API evolves. We are grateful to the Kanban Zone team for their collaboration and for making a first-class API available to the AI-assistant ecosystem.
