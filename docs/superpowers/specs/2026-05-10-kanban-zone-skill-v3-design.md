# Kanban Zone Skill v3.0.0 — Design Spec

- **Date:** 2026-05-10
- **Skill repo:** `kanban-zone`
- **Wraps:** Kanban Zone Public API v1.4.0 (`https://integrations.kanbanzone.io/v1/`)
- **Bumps from:** v2.1.0 (which wrapped API v1.3)
- **Status:** Brainstorming complete; awaiting implementation plan.

## 1. Goal

Update the Kanban Zone skill to cover every endpoint in API v1.4.0 — comments, checklists, tasks, card share tokens, full webhook CRUD, eight reports, organization context, card history/metrics, board sub-resources (labels, members, custom fields, templates), card delete — and modernize the skill's CLI surface to scale as Kanban Zone keeps adding endpoints.

This is being published in partnership with Kanban Zone (the company); the API additions in v1.4 were made in direct response to this skill's needs. The bar is "official, polished, rock-solid."

## 2. Decisions (brainstorming summary)

| # | Question | Decision |
|---|----------|----------|
| 1 | MCP vs skill | **Skill remains primary.** The official `kanban-zone-mcp-server` is acknowledged but neither wrapped nor replaced. The skill keeps its deterministic CLI, agent cache, and delete operations (which MCP intentionally omits). |
| 2 | Card identifier in CLI | **Auto-detect:** numeric → card number, 24-hex string → ObjectId. Single `--id` flag. |
| 3 | CLI organization | **Full grouped reorganization** (`cards create`, `boards list`, etc.) — v3.0.0 breaking change. Old flat commands kept as **hidden back-compat aliases** with `argparse.SUPPRESS`. |
| 4 | Code organization | **Split into a small `scripts/kanban_zone/` package** — CLI entry stays at `scripts/kanban_zone_api.py` (~150 lines), each resource gets its own module. |
| 5 | Test framework | **stdlib `unittest` + mocked HTTP.** No third-party dependency at runtime. Coverage tooling (`coverage.py`) is a documented dev dep. |
| 6 | Endpoint deprecation | **Silent migration** to all new canonical paths (`PATCH /cards/{id}`, `POST /checklists`, `POST /comments`, `POST /tokens`, `GET /boards/{publicId}`). No fallback toggle. |
| 7 | Reports CLI shape | **One subcommand per report type** (8 wrappers over a shared `_run_report` helper). |
| 8 | Webhook signature helper | **Yes — `webhooks verify-signature`.** Pure-local HMAC-SHA1 helper, no network call. |

Coverage target raised platform-wide from 80 % to **≥ 95 %** for this skill, since it's a public, official open-source release.

## 3. Inventory: API surface

### 3.1 Currently covered (v1.3, in v2.1 skill)

`GET /boards`, `GET /board/{board}` (now deprecated), `GET /cards`, `GET /card`, `POST /card`, `POST /cards`, `PUT /card/{id}` (now deprecated), `POST /card/{id}/move`. ~12 endpoints, 12 flat CLI commands.

### 3.2 Newly added in v1.4 (must be covered)

**Cards (new):**
- `PATCH /cards/{id}` — replaces `PUT /card/{id}`
- `DELETE /cards/{id}`
- `GET /cards/{id}` — fetch by ObjectId
- `GET /cards/{id}/history`
- `GET /cards/{id}/metrics`

**Boards sub-resources (new):**
- `GET /boards/{publicId}` — replaces `GET /board/{board}`
- `GET /boards/{publicId}/columns`
- `GET /boards/{publicId}/labels`
- `GET /boards/{publicId}/members`
- `GET /boards/{publicId}/custom-fields`
- `GET /boards/{publicId}/reports/{reportType}` — 8 types

**Comments (new):**
- `POST /comments`
- `GET /cards/{id}/comments`
- (`POST /cards/{id}/comments` deprecated)

**Checklists (new):**
- `POST /checklists`
- `PATCH /checklists/{id}`
- `DELETE /checklists/{id}`
- `GET /cards/{id}/checklists`
- (`POST /cards/{id}/checklists` deprecated)

**Tasks (new):**
- `POST /tasks`
- `PATCH /tasks/{id}`
- `DELETE /tasks/{id}`
- `POST /tasks/{id}/move`

**Tokens (card share tokens — new):**
- `POST /tokens`
- `DELETE /tokens/{id}`
- `GET /cards/{id}/tokens`
- (`POST /cards/{id}/tokens` deprecated)

**Webhooks (CRUD — was UI-only):**
- `GET /webhooks`
- `GET /webhooks/{id}`
- `POST /webhooks`
- `PUT /webhooks/{id}`
- `DELETE /webhooks/{id}`
- `POST /webhooks/{id}/test`

**Organization (new):**
- `GET /me`
- `GET /organization`

**Templates (new — board-scoped):**
- `GET /templates/{publicId}` — `publicId` is the board's public id; lists card templates for that board.

### 3.3 Webhook events
v1.4 adds `CARD_UPDATED` (was `CARD_CREATED`/`CARD_MOVED` only). Three event names accepted by `webhooks create`/`update`. Signature verification is documented as mandatory: HMAC-SHA1 over the JSON-stringified payload, signed with the org's Webhook Key, sent in `X-KanbanZone-Signature`.

## 4. CLI command surface

### 4.1 Grouped surface (the *only* surface in `--help` and docs)

```
boards      list | get | columns | labels | members | custom-fields | templates
cards       list | get | create | create-bulk | update | move | delete
            | history | metrics | links-add | links-remove | search | wip-check
comments    list | add
checklists  list | create | update | delete
tasks       create | update | delete | move
webhooks    list | get | create | update | delete | test | verify-signature
reports     throughput | arrival-rate | cycle-time | lead-time
            | flow | flow-efficiency | allocation | abandoned-effort
tokens      list | assign | revoke
org         me | context
```

Notes:
- `cards search` and `cards wip-check` keep today's behavior (cross-board search; WIP report for the active board).
- `cards links-add` / `cards links-remove` replace today's `link-card` / `unlink-card`. They use the v1.4 `links` sub-schema on `PATCH /cards/{id}`.
- `cards create-bulk` reads JSON from `--file` (same shape as today's `create-cards`).
- `boards templates --board <id>` lists card templates for a board (`GET /templates/{publicId}`). Templates belong to a board, so they live in the boards group.
- `cards get --id <number-or-oid>` always resolves to `GET /cards/{ObjectId}`. The deprecated singular `GET /card?board=...&number=...` is not used; lookup-by-number goes through cache → on miss, paged `GET /cards?board=...` until the matching number is found, then both directions are written to the cache before the ObjectId fetch.

### 4.2 Hidden back-compat aliases (work, but suppressed from `--help`)

| v2 flat command | v3 grouped equivalent |
|-----------------|------------------------|
| `boards`        | `boards list`          |
| `board`         | `boards get`           |
| `cards`         | `cards list`           |
| `card`          | `cards get`            |
| `create-card`   | `cards create`         |
| `create-cards`  | `cards create-bulk`    |
| `update-card`   | `cards update`         |
| `move-card`     | `cards move`           |
| `link-card`     | `cards links-add`      |
| `unlink-card`   | `cards links-remove`   |
| `search-cards`  | `cards search`         |
| `wip-check`     | `cards wip-check`      |

Implementation: every alias is registered as a top-level subparser with `help=argparse.SUPPRESS`. Each alias's handler is a one-liner that constructs the grouped equivalent's `argparse.Namespace` and calls the grouped handler. A code comment on each alias explains the mapping.

### 4.3 Global flags (root parser)

- `--board <id>` — overrides `KANBAN_ZONE_BOARD_ID` env for one invocation.
- `--no-cache` — bypass cache; do not read or write `kanbanzone-cache.json`.
- `--pretty` — pretty-print JSON output (default: compact).
- `--api-token <base64>` — overrides env, primarily for tests.

## 5. Repository layout

```
kanban-zone/
├── SKILL.md                      # rewritten — agent-facing, grouped commands only
├── README.md                     # rewritten — install + cookbook
├── AGENTS.md                     # rewritten — contributor guide + sync clause
├── CHANGELOG.md                  # NEW — semver history starting at v3.0.0
├── LICENSE.txt                   # unchanged
├── .clawhubignore                # unchanged
├── .gitignore                    # add tests/__pycache__, .coverage, htmlcov/
├── Makefile                      # NEW — `make test`, `make coverage`, `make lint`
├── docs/superpowers/specs/
│   └── 2026-05-10-kanban-zone-skill-v3-design.md   # this file
├── references/
│   ├── api-reference.md          # rewritten — full v1.4 endpoint + schema reference
│   └── migration-from-v2.md      # NEW — flat → grouped command map
├── scripts/
│   ├── kanban_zone_api.py        # CLI entry (~150 lines: argparse wiring + dispatch)
│   └── kanban_zone/
│       ├── __init__.py
│       ├── http.py               # auth, base64 key, api_request, error model
│       ├── cache.py              # board/column cache + bidirectional number↔ObjectId
│       ├── ids.py                # auto-detect + bidirectional resolvers
│       ├── output.py             # JSON output, --pretty, error formatting
│       ├── boards.py
│       ├── cards.py
│       ├── comments.py
│       ├── checklists.py
│       ├── tasks.py
│       ├── webhooks.py           # webhooks group + verify-signature helper
│       ├── reports.py            # 8 wrappers over shared _run_report
│       ├── tokens.py
│       ├── org.py
│       └── legacy.py             # hidden flat aliases → grouped handlers
└── tests/
    ├── __init__.py
    ├── fakes.py                  # FakeApi: programmable api_request stand-in
    ├── fixtures/                 # sanitized JSON sample responses
    │   ├── card.json
    │   ├── cards_list.json
    │   ├── board.json
    │   ├── boards_list.json
    │   ├── checklist.json
    │   ├── webhook.json
    │   ├── report_throughput.json
    │   └── ...                   # one per resource and report type
    ├── test_http.py
    ├── test_cache.py
    ├── test_ids.py
    ├── test_output.py
    ├── test_boards.py
    ├── test_cards.py
    ├── test_comments.py
    ├── test_checklists.py
    ├── test_tasks.py
    ├── test_webhooks.py          # incl. verify-signature pass + fail
    ├── test_reports.py           # all 8 types
    ├── test_tokens.py
    ├── test_org.py
    ├── test_legacy_aliases.py
    └── test_cli_help.py
```

## 6. Behavior details

### 6.1 HTTP layer (`kanban_zone/http.py`)

- `BASE_URL = "https://integrations.kanbanzone.io/v1"`.
- Signature: `api_request(method, path, params=None, body=None) -> Any` (returns the parsed JSON value — typically a `dict`, occasionally a `list` for collection endpoints, occasionally `None` on 204).
- Builds the Authorization header from `KANBAN_ZONE_API_KEY`, base64-encoded once at first call (in-process cache).
- Sends with `urllib.request.Request`. Reads JSON response.
- Adds header `User-Agent: kanban-zone-skill/3.0.0`.
- On non-2xx: raises `KanbanZoneApiError(status, body, request_line)`. Caught at the CLI boundary and rendered as `{"error": true, "status": N, "message": "..."}` on stderr; exit code 1.
- `.env` auto-loading remains exactly as in v2: search current working directory, then the skill's parent directory.

### 6.2 ID resolution (`kanban_zone/ids.py`)

- `detect_id_kind(value: str) -> Literal["number", "object_id"]`. Matches `^\d+$` → `"number"`; matches `^[0-9a-fA-F]{24}$` → `"object_id"`; else raises `KanbanZoneIdError`.
- `resolve_card_object_id(value, board, cache) -> str`:
  - if `value` is already an ObjectId, return it;
  - if `value` is a number, check `cache.get_card_oid(board, number)`;
  - on cache miss, page through `GET /cards?board=...&page=N&count=100` until the card whose `number` field matches is found (v1.4 has no `number` query filter, and the legacy `GET /card?board=...&number=...` is not used);
  - persist both directions in the cache before returning the ObjectId.
- `resolve_card_number(object_id, board, cache) -> int`: symmetrical reverse direction. Used only when display logic needs to show a number for an ObjectId-keyed response.
- All resolution functions accept the cache as an argument (no global cache state) so tests can pass a fake.

### 6.3 Cache (`kanban_zone/cache.py`)

- File: `kanbanzone-cache.json` in the agent's memory directory (location *unchanged from v2*; the path is supplied by the CLI entry, not read from env inside the cache module).
- Schema:

  ```json
  {
    "boards": {
      "<board-public-id>": {
        "name": "Board Name",
        "columns": {
          "<col-id>": { "name": "Column Name", "state": "In Progress" }
        },
        "cards": {
          "byNumber":   { "42":   "<card-object-id>" },
          "byObjectId": { "<id>": 42 }
        }
      }
    },
    "updated": "2026-05-10T00:00:00Z"
  }
  ```

- `Cache` class:
  - Atomic write via `tempfile.NamedTemporaryFile` + `os.replace`.
  - Methods: `get_board(public_id)`, `set_board(public_id, name)`, `get_column(public_id, column_id)`, `set_columns(public_id, columns)`, `get_card_oid(public_id, number)`, `get_card_number(public_id, object_id)`, `set_card_mapping(public_id, number, object_id)`, `invalidate_card(public_id, number_or_oid)`, `flush()`.
- Forward compatibility: a v2 cache file lacking `cards.byNumber`/`byObjectId` is read normally; new keys are added on first write that produces them.
- `--no-cache` global flag forces fresh API calls and short-circuits all read/write.

### 6.4 Endpoint migration (silent)

| Old (v2 calls) | New (v3 calls) |
|----------------|----------------|
| `PUT /card/{id}` | `PATCH /cards/{id}` (id = ObjectId) |
| `POST /cards/{id}/checklists` | `POST /checklists` (`{"card": "<oid>", ...}`) |
| `POST /cards/{id}/comments` | `POST /comments` (`{"card": "<oid>", ...}`) |
| `POST /cards/{id}/tokens` | `POST /tokens` (`{"card": "<oid>", ...}`) |
| `GET /board/{board}` | `GET /boards/{publicId}` |

For every command that takes a card number argument and ends up calling an ObjectId-based endpoint (e.g., `cards update --id 42`), the CLI resolves the number → ObjectId via the cache/lookup before the call. The user-facing JSON output retains the `number` field where the API returns it; nothing in the output shape changes.

### 6.5 Webhook signature helper (`webhooks verify-signature`)

- Pure local: `hmac.new(key.encode(), payload_bytes, hashlib.sha1).hexdigest()`.
- Reads the payload from `--payload-file` (binary read). Documented expectation: the file contains exactly the bytes that were signed — i.e. the value of `notification.payload` (as the docs' verification example does), not the full envelope.
- Reads the key from `--webhook-key` or `KANBAN_ZONE_WEBHOOK_KEY`.
- Compares using `hmac.compare_digest`.
- Output: `{"verified": true|false, "computed": "<hex>"}`. Exit 0 on match, 1 on mismatch.

### 6.6 Pagination

- `cards list` exposes `--page <N>` (default 1) and `--count <N>` (default 100, max 100). Response shape (`hasMore`, `totalAvailable`) passes through unchanged.
- The `fetch_all_cards` helper that loops pages stays — used by `cards search` and `cards wip-check` so they remain "see everything" commands.

## 7. Testing

### 7.1 Strategy

- stdlib `unittest`, mocked HTTP.
- Single fake at `tests/fakes.py`: `FakeApi` is a context manager that monkey-patches `kanban_zone.http.api_request` with a programmable response queue.
  - `expect(method, path, params=..., body=...).returns(json=..., status=200)` style.
  - `assert_no_more_calls()` verifies the queue is drained.
  - Per-call assertion: method, path, params, body match what the test queued.
- `tests/fixtures/` holds real-shape sanitized JSON loaded by helpers, never pasted inline.
- `Cache` tests use `tempfile.TemporaryDirectory` with the cache file path injected via constructor.
- `test_http.py` exercises real `urllib.request` against an `http.server.BaseHTTPRequestHandler` running on an ephemeral port — covers auth header, base64 encoding, error mapping, User-Agent.
- `test_legacy_aliases.py` parametric: list of `(legacy_argv, expected_grouped_handler, expected_kwargs)` — each case asserts the alias dispatches correctly.
- `test_cli_help.py` invokes the CLI as a subprocess and asserts:
  - root `--help` lists every grouped command;
  - root `--help` lists no legacy alias;
  - each group has at least one subcommand with non-empty help text.
- `test_webhooks.py` covers `verify-signature` with a known-good `(payload, key, signature)` fixture and a known-bad case.

### 7.2 Coverage

- Target: **≥ 95 % line coverage**.
- Tooling: `coverage.py` (dev dep, not runtime).
- CI command: `coverage run -m unittest discover tests && coverage report --fail-under=95`.
- A small `Makefile` at repo root exposes `make test`, `make coverage`, `make lint`.

## 8. Documentation

| File | Treatment |
|------|-----------|
| `SKILL.md` | Full rewrite. Sections: agent quick-start (env + .env), grouped command surface (one section per resource group with 2–3 example invocations each), description-formatting rules (HTML, no tables, `<pre>` blocks — kept verbatim from v2), exec-safety rule for multi-line strings (kept), `--description-file` workflow (kept), cache section (updated with bidirectional ID-mapping note), column-states table (kept), script-reference table covering grouped subcommands. Legacy aliases get one sentence pointing to `references/migration-from-v2.md` — not enumerated in SKILL.md. |
| `README.md` | Full rewrite as the published face. Sections: what the skill does, install, env setup, worked-example cookbook (8–10 realistic flows), the API version it wraps (v1.4), and a "What's new in v3" pointing to CHANGELOG. |
| `AGENTS.md` | Full rewrite for contributors. Sections: project layout (the `kanban_zone/` package), how to add a new endpoint (template: handler in `kanban_zone/<resource>.py`, register subparser, add fixture, add test, run coverage), test commands, coverage requirement, commit-style alignment with the parent platform. Includes the SKILL.md/AGENTS.md sync clause. |
| `references/api-reference.md` | Full rewrite covering every v1.4 endpoint with parameters, request body schema, response shape, and notes on deprecated equivalents. Sourced from the Postman collection plus the live SPA pages. Replaces today's v1.3 reference. |
| `references/migration-from-v2.md` | NEW. The flat-to-grouped command map (table), how the hidden aliases work, the silent endpoint migration list, and the cache schema migration note. |
| `CHANGELOG.md` | NEW. v3.0.0 entry covering: API v1.4 coverage, grouped CLI, hidden aliases, bidirectional ID cache, silent endpoint migration, signature-verify helper, ≥95 % coverage. Older versions reconstructed best-effort from git history (v2.1.0, v2.0.0). |

## 9. Migration semantics for existing users

- All existing flat commands keep working unchanged (hidden aliases). Zero hard breakage.
- Anyone reading `--help` sees only the grouped surface — incentive to migrate.
- Cache file is forward-compatible: old `kanbanzone-cache.json` files (no `cards` block) read as-is; new keys populate lazily.
- `.env` keys (`KANBAN_ZONE_API_KEY`, `KANBAN_ZONE_BOARD_ID`) unchanged.
- Wire-level behavior for the existing commands changes (PUT → PATCH, etc.) but JSON output shape stays the same.

## 10. Out of scope

- Hosted MCP server. The official `kanban-zone-mcp-server` exists separately; this skill does not wrap or replace it.
- Zapier integration management (no public Zapier API exposed beyond what the docs already show).
- Distribution as a `pip install`-able library. The package layout means `from kanban_zone import cards` works for tests, but no PyPI publishing.
- OpenAPI codegen. Implementation works from the Postman collection plus live docs scrape.

## 11. Acceptance criteria

The implementation is done when:

1. Every endpoint listed in §3.2 is reachable through the grouped CLI surface in §4.1.
2. Every command in §4.2 still works as a hidden alias (covered by `test_legacy_aliases.py`).
3. The bidirectional cache (§6.3) is exercised by tests that show a cache hit avoids the API and a cache miss writes both directions.
4. The webhook signature helper (§6.5) returns the correct exit code for both pass and fail fixtures.
5. `coverage report --fail-under=95` succeeds.
6. SKILL.md, README.md, AGENTS.md, references/api-reference.md, references/migration-from-v2.md, and CHANGELOG.md all reflect v3.0.0 content. Stale v1.3 mentions are allowed only inside `CHANGELOG.md`, `references/migration-from-v2.md`, and any "deprecated equivalent" notes in `references/api-reference.md` — anywhere else they are reviewer-flagged.
7. SKILL.md and AGENTS.md both contain the prominent sync instruction; both files are up-to-date in the same commit.
