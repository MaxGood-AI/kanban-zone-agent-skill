# Repository Guidelines

## Overview

This repository contains a Claude Skill for interacting with Kanban Zone kanban boards. It is a single-file Python CLI (`scripts/kanban_zone_api.py`) using only the Python standard library.

## File Roles

- **SKILL.md** -- Claude Skill definition file. This is what Claude Code reads when the skill is invoked. It describes available commands, workflows, and configuration. Keep it in sync with the actual CLI capabilities.
- **scripts/kanban_zone_api.py** -- The CLI implementation. All commands output JSON to stdout.
- **references/api-reference.md** -- Kanban Zone Public API v1.3 documentation. Use this as the source of truth for endpoints, request/response models, and field definitions.

## Adding a New Command

1. Write a `cmd_<name>(args)` handler function in `scripts/kanban_zone_api.py`.
2. Add a subparser for the command in `build_parser()`.
3. Add the command name and handler to the `commands` dict in `main()`.
4. Update `SKILL.md` to document the new command in both the Quick Start examples and the Script Reference table.

## Environment Setup

Two environment variables are required:
- `KANBAN_ZONE_API_KEY` -- Raw API key from Kanban Zone (Settings > Organization Settings > Integrations > API Key). The script Base64-encodes it automatically.
- `KANBAN_ZONE_BOARD_ID` -- Default board public ID. Can be overridden per command with `--board`.

## Code Style

- Python: PEP 8, 4-space indentation, `snake_case` functions and variables.
- No third-party dependencies. stdlib only.
- All CLI output must be valid JSON via `json.dump` to stdout.
- Errors must exit with `error_exit()` which outputs JSON and sets exit code 1.

## Testing

There is no test suite. To verify changes, run commands against a real Kanban Zone board with valid credentials:
```bash
export KANBAN_ZONE_API_KEY="your-key"
export KANBAN_ZONE_BOARD_ID="your-board-id"
python3 scripts/kanban_zone_api.py boards
python3 scripts/kanban_zone_api.py board --include-columns
python3 scripts/kanban_zone_api.py cards
```

## Commit Style

- **Subject line**: short imperative verb phrase under ~72 chars (e.g., `Fix oversized content chunks`). Start with a verb: `Add`, `Fix`, `Update`.
- **Body** (for non-trivial changes): use markdown formatting with `## Problem`, `## Solution`, and `## Verified` sections to explain *why* the change was made, *what* was done, and *how* it was validated. If the change adds or modifies environment variables, note the impact in the body.
- **Trivial changes**: only typo corrections are considered trivial and may omit the body. All other changes deserve the full message format.
- **Kanban Zone**: append the relevant Roadmap board card URL (e.g., `https://kanbanzone.io/b/QJxJGohF/c/298`) as the last line before `Co-Authored-By`.
- **Co-authorship**: when AI-assisted, end with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` (or the model used).

## API Notes

- Base URL: `https://integrations.kanbanzone.io/v1`
- Auth: `Authorization: Basic {base64-encoded-key}`
- Rate limits: Professional plan gets 1,000 calls/month; Enterprise is unlimited; Free/Basic plans have no API access.
- The `ColumnItemOutputModel.boardTitle` field contains the column ID, not a board title.
- Card numbers (integers) are used as IDs in update and move operations.
- Mirrored card operations require a `board` field in the request body.
- **Card descriptions are HTML, and HTML tables are silently stripped.** Use `<pre>` with fixed-width ASCII for tabular data — never `<table>`/`<tr>`/`<td>`. See SKILL.md and README.md for examples.

## Synchronization Rule

If both `AGENTS.md` and `CLAUDE.md` exist in this directory, they must be identical in content and updated together in the same commit. Do not allow them to drift.
