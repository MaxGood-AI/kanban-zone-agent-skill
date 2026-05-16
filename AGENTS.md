# Repository Guidelines

## CLAUDE.md / AGENTS.md Synchronization

**CLAUDE.md / AGENTS.md sync:** if both files exist in this repo, they MUST be identical and updated together in the same commit. SKILL.md and AGENTS.md are NOT required to be identical — SKILL.md is agent-facing, AGENTS.md is contributor-facing.

## Project Layout

The kanban-zone v3 skill is organized as a modular Python package under `scripts/kanban_zone/` with one module per resource type, plus support modules for cross-cutting concerns:

```
scripts/
├── kanban_zone/
│   ├── __init__.py             # Package marker
│   ├── http.py                 # HTTP client wrapper; handles auth, encoding, error handling
│   ├── output.py               # JSON output formatter; pretty-printing
│   ├── cache.py                # Simple in-memory result cache; key-based with TTL
│   ├── ids.py                  # ID transformation utilities (string/int conversion, normalization)
│   ├── boards.py               # boards, board, columns, labels, members, custom-fields, templates
│   ├── cards.py                # cards, card, create-card, create-cards, update-card, move-card, links-*
│   ├── comments.py             # card-comment, card-comments
│   ├── checklists.py           # checklist, create-checklist, update-checklist, delete-checklist
│   ├── tasks.py                # task, create-task, update-task, delete-task, move-task
│   ├── tokens.py               # assign-token, revoke-token, tokens
│   ├── webhooks.py             # webhook, create-webhook, delete-webhook + signature verification
│   ├── reports.py              # 8 report commands (throughput, arrival-rate, cycle-time, lead-time, flow, flow-efficiency, allocation, abandoned-effort)
│   ├── org.py                  # me, context (organization info)
│   └── legacy.py               # v2 backward-compatibility aliases
├── kanban_zone_api.py          # CLI entry point; argument parsing and dispatch
├── sessionstart-repo-status.py # SessionStart hook (not part of main CLI)
└── requirements.txt            # Dependencies (currently none; stdlib only)

tests/
├── __init__.py
├── fakes.py                    # FakeApi mock for testing; in-memory board model
├── test_http.py                # kanban_zone.http tests
├── test_output.py              # kanban_zone.output tests
├── test_cache.py               # kanban_zone.cache tests
├── test_ids.py                 # kanban_zone.ids tests
├── test_org.py                 # org module tests (me, context)
├── test_boards.py              # boards module tests (7 subcommands)
├── test_cards_read.py          # cards read operations (list, get)
├── test_cards_write.py         # cards write operations (create, update, move)
├── test_cards_misc.py          # cards links, search, wip-check
├── test_comments.py            # comments module tests
├── test_checklists.py          # checklists module tests
├── test_tasks.py               # tasks module tests
├── test_tokens.py              # tokens module tests
├── test_webhooks.py            # webhooks module + signature verification tests
├── test_reports.py             # reports module tests (8 report types)
├── test_legacy_aliases.py      # v2 backward-compatibility aliases
├── test_cli_help.py            # Help text and subcommand registration
├── test_fakes.py               # FakeApi tests
└── fixtures/
    ├── .gitkeep
    └── boards_list.json        # Sample board data for tests
```

**Module responsibilities:**

- **http.py**: HTTP client; handles Authorization header (base64 encoding), JSON encoding/decoding, error responses. Single entry point: `api_request(method, path, params={}, body=None)`.
- **output.py**: JSON output to stdout; `print_json(data, pretty=False)`. Ensures all commands produce valid JSON.
- **cache.py**: Simple key-value cache with optional TTL. Used by expensive read operations to reduce API calls during tests and in production.
- **ids.py**: Normalize and convert card IDs between string (v3) and integer (v2) formats. Helpers: `str_id(x)`, `int_id(x)`, etc.
- **boards.py**: Board operations — list boards, get board by ID, fetch columns, labels, members, custom fields, board templates.
- **cards.py**: Card CRUD — list, get, create, update, move. Links management (add, remove). Search and WIP-check helpers.
- **comments.py**: Card comments — add comment to card, list comments on a card.
- **checklists.py**: Checklist CRUD — create on card, update, delete, list items.
- **tasks.py**: Task CRUD — create, read, update, delete, and move tasks within checklists.
- **tokens.py**: Token (user assignment) management — assign tokens to cards, revoke, list assigned.
- **webhooks.py**: Webhook CRUD and signature verification. Supports event subscription and HMAC-SHA1 signature validation.
- **reports.py**: 8 reports (throughput, arrival-rate, cycle-time, lead-time, flow, flow-efficiency, allocation, abandoned-effort) wrapping the Kanban Zone reports API at /boards/{publicId}/reports/{type}.
- **org.py**: Organization context — `me` (current user) and `context` (org info).
- **legacy.py**: v2 backward-compatibility wrappers. Accepts v2 CLI syntax (e.g., integer card IDs) and wraps v3 handlers.

## Known API Limitation — Delete Operations

Kanban Zone's DELETE endpoints are non-functional server-side. Every DELETE
(`/cards`, `/checklists`, `/tasks`, `/webhooks`, `/tokens`) is answered with
`HTTP 200` + `{"message": "Body Parser failed ..."}` and never deletes the
record — Kanban Zone's API edge (AWS CloudFront / API Gateway) strips the
request body, and the DELETE routes then reject the now-empty body. No
request shape works around it. (Confirmed live 2026-05-16; reported to
Kanban Zone.)

Implications for contributors:

- All five delete commands route through `http.delete_resource()`, which
  raises `KanbanZoneDeleteUnsupportedError` (a `KanbanZoneApiError` subclass)
  carrying a message written for both humans and AI agents. Do **not** "fix"
  a failing delete by retrying, changing the request body, or suppressing the
  error — the defect is in Kanban Zone's API, not this skill.
- Regression coverage lives in `tests/test_delete_endpoint.py`.
- When Kanban Zone ships a server-side fix, restore a plain success path in
  the delete commands and remove the warning sections from `README.md` and
  `SKILL.md`.

## Adding a New Endpoint: Step-by-Step Template

When adding a new endpoint or subcommand, follow this repeatable loop:

### 1. Create a fixture (if needed)

If your test needs sample API response data, create a JSON fixture file:

```bash
# Create tests/fixtures/<resource-name>.json with representative API response
cat > tests/fixtures/my_resource.json <<'EOF'
{
  "id": "123",
  "name": "Example",
  "created": "2026-05-10T00:00:00Z"
}
EOF
```

**Why:** Fixtures are the ground truth for response shape; they let you verify your test reads the right fields without hitting the real API.

### 2. Write a failing test

Create a test file `tests/test_<resource>.py` (or add to an existing one):

```python
import unittest
from tests.fakes import FakeApi
from kanban_zone import <resource>  # import the module you're testing

class TestMyResource(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.api.set_board("test-board-id")

    def test_my_new_command(self):
        """Test description of what the command does."""
        # Arrange: set up fake data
        self.api.create_card({
            "id": "1",
            "title": "Test Card",
        })

        # Act: call your handler
        args = argparse.Namespace(
            board="test-board-id",
            some_param="value",
        )
        ctx = argparse.Namespace(
            board="test-board-id",
            pretty=False,
        )
        <resource>.cmd_my_command(args, ctx)

        # Assert: verify output or side effects
        # (If the command calls print_json, capture stdout)

if __name__ == "__main__":
    unittest.main()
```

**Why:** Test-first ensures your command's inputs and outputs are clear before you implement. Failing tests define what "done" means.

### 3. Implement the handler

In `scripts/kanban_zone/<resource>.py`, add:

```python
def cmd_my_command(args, ctx):
    """Docstring explaining the command."""
    # Validate required args
    if not args.my_required_arg:
        raise ValueError("--my-required-arg is required")

    # Call the API
    resp = kanban_zone_http.api_request("GET", f"/my-endpoint/{args.id}", params={
        "someParam": args.some_param,
    })

    # Output JSON
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)
```

**Module-level pattern:** all handlers have signature `cmd_<name>(args, ctx)` where:
- `args` is an `argparse.Namespace` with parsed CLI arguments
- `ctx` is an `argparse.Namespace` with shared context (board ID, pretty-print flag, etc.)

### 4. Register the subparser

In `scripts/kanban_zone_api.py`, find the `register()` function and add your command:

```python
def register(subparsers):
    # ... existing commands ...

    def _add_my_command(subparsers):
        p = subparsers.add_parser("my-command", help="Short description of my-command")
        p.add_argument("--my-required-arg", required=True, help="Description")
        p.add_argument("--my-optional-arg", default="default-value", help="Description")
        p.set_defaults(handler=kanban_zone_<resource>.cmd_my_command)

    _add_my_command(subparsers)
```

**Why:** Subparser registration couples the CLI arg spec to the handler; keeping them together in one block prevents drift.

### 5. Run your test

```bash
python3 -m unittest tests.test_<resource>.TestMyClass.test_my_command
```

Verify it passes. If it fails, fix the handler and re-run.

### 6. Check coverage

```bash
make coverage
```

Ensure the overall coverage remains ≥95%. If a line is unreachable or truly optional, mark it with a `# pragma: no cover` comment and note why.

### 7. Update the help test

In `tests/test_cli_help.py`, update the `GROUPS_AND_SUBCOMMANDS` dict to include your new subcommand:

```python
GROUPS_AND_SUBCOMMANDS = {
    "my-group": ["my-command", "my-other-command"],  # add here
}
```

Run the help test to verify the command is discoverable:

```bash
python3 -m unittest tests.test_cli_help
```

### 8. Commit

Once all tests pass and coverage is ≥95%, commit with a clear message:

```bash
git add scripts/kanban_zone/<resource>.py tests/test_<resource>.py tests/fixtures/<name>.json
git commit -m "$(cat <<'EOF'
Add my-command subcommand

## Problem
Users needed a way to [describe the user need].

## Solution
Added cmd_my_command() handler in kanban_zone.<resource> with --my-required-arg and --my-optional-arg.
Test coverage is comprehensive with fixtures in tests/fixtures/<name>.json.

## Verified
python3 -m unittest tests.test_<resource>
make coverage  # ≥95%

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Test Commands

Run tests locally using `make`:

```bash
make test              # Run all unit tests; exit code 0 if all pass
make coverage          # Run tests with coverage report; must be ≥95%
make coverage-html     # Generate htmlcov/index.html (open in browser for detailed report)
make lint              # Run flake8 and pylint; zero-warning policy enforced
```

All services must pass `make lint` with zero warnings before a commit.

## Coverage Requirement

- **Minimum: 95% line coverage.** All non-trivial code must be tested.
- **Policy:** Pull requests that drop coverage below 95% must add tests to restore the threshold. Never lower the threshold to accommodate untested code.
- **Pragma exceptions:** Mark unreachable or intentionally-untested lines with `# pragma: no cover` and document the reason in the same commit that adds the coverage threshold.

## Commit Style

Follow the platform CLAUDE.md commit conventions:

- **Subject line:** Imperative verb phrase ≤72 characters. Examples: `Add my-command subcommand`, `Fix card ID validation`, `Update webhook signature check`.
- **Body (for non-trivial changes):** Use markdown with `## Problem`, `## Solution`, and `## Verified` sections:
  - `## Problem`: Why was this change needed? What user pain or code smell drove it?
  - `## Solution`: What did you implement? What files changed?
  - `## Verified`: How did you test it? List the exact commands run and their output.
- **Trivial changes** (typos, comment fixes): subject line only, no body needed.
- **Kanban Zone link** (if applicable): Append the card URL as the last line before trailers. Example: `https://kanbanzone.io/b/QJxJGohF/c/298`
- **Co-authorship:** End with `Co-Authored-By: <Model Name> <email>`. Example: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`

**Example commit message:**

```
Add card-comment subcommand

## Problem
Users could not add comments to cards via the CLI; only read-only operations existed.

## Solution
Implemented cmd_add_comment() in kanban_zone.comments with --id and --text arguments.
Handler calls POST /cards/<id>/comments with the comment body.
Added test_comments.py with FakeApi-based unit tests covering both success and error paths.

## Verified
python3 -m unittest tests.test_comments
make coverage  # 97% overall

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## No Multi-Line Shell Commands

Do NOT use heredocs or multi-line quoted strings in bash tool calls. This rule prevents shell-escaping gotchas and keeps the command readable.

Instead, write scripts to temp files and execute:

```bash
# WRONG: Do not do this
python3 -c "
import json
lines = []
for x in range(10):
    lines.append(str(x))
"

# RIGHT: Use a temp file
cat > /tmp/my_script.py <<'EOF'
import json
lines = []
for x in range(10):
    lines.append(str(x))
EOF
python3 /tmp/my_script.py
```

This is a v2 rule carried forward to v3 to maintain consistency.

