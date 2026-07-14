# Changelog

All notable changes to the Kanban Zone skill. Versioning follows SemVer.

## [3.2.0] — 2026-07-14

### Fixed
- When the organization's **monthly API usage limit** is exhausted, Kanban
  Zone rejects every call with HTTP 200 and the error only in the body
  (`{"code": 2006, "status": 429, "name": "TooManyRequests", "message":
  "API Usage limit reached"}`). The skill passed that envelope through as if
  it were data, so callers saw empty results instead of an error — most
  damagingly, the card-number resolver scanned "0 of None cards" and reported
  a misleading `Card number N not found` for cards that exist. Confirmed
  live 2026-06-11.

### Added
- `http._raise_on_error_envelope()`: every 2xx response body is now checked
  for a hidden Kanban Zone error envelope. The code-2006 / `TooManyRequests`
  shape raises the new `KanbanZoneUsageLimitError` (exit non-zero) with an
  agent-readable message stating the request was rejected, that retrying is
  futile until the monthly quota resets or the plan limit is raised, and
  directing the user to the **Organization > Integrations** panel
  (https://kanbanzone.io/settings/integrations) to check the "Available API
  Calls" meter. Any other envelope carrying a numeric `status` >= 400 plus
  `name` and `message` keys raises a plain `KanbanZoneApiError` with the
  body's status.
- "Monthly API usage limit" sections in `README.md` and `SKILL.md` with
  do-not-retry guidance for agents.

### Changed
- **Kanban Zone fixed its DELETE API (2026-06-11)** — the server-side
  "Body Parser failed" defect that broke every DELETE endpoint since
  2026-05-16 is resolved, and all five delete commands (`cards delete`,
  `checklists delete`, `tasks delete`, `webhooks delete`, `tokens revoke`)
  work normally again. The warning sections in `README.md`, `SKILL.md`, and
  `AGENTS.md` are replaced with historical notes, and the per-command ⚠️
  annotations are removed. `http.delete_resource()` keeps the failure-envelope
  detection as a regression guard (now worded as such): a returning defect
  fails loudly instead of reporting a fake success.

## [3.1.2] — 2026-05-18

### Fixed
- `cards search` crashed with `KeyError: 'publicId'` on every invocation.
  The `/boards` API wraps each board in a `BoardItem` envelope (the
  board-level counterpart of the `CardItem` envelope), but `cmd_search`
  read `publicId` directly off the envelope. A new `_unwrap_board()` helper
  flattens the envelope before the lookup; already-flat board dicts still
  work. The existing search test used flat fixtures that never matched the
  real API shape, so it masked the bug — it now uses the `BoardItem`
  envelope, with an added test covering the flat shape.
- `.env` auto-discovery was fragile: it checked only the current working
  directory and the script's immediate parent, and used a non-symlink-resolved
  path. When the skill is installed as a symlink (e.g.
  `~/.claude/skills/kanban-zone`) and invoked from any other directory, the
  workspace `.env` was never found, so every command failed with
  `--board ... is required` / `KANBAN_ZONE_API_KEY is not set`. Discovery now
  resolves symlinks and walks every ancestor of both the cwd and the script's
  real location, so a workspace-root `.env` is found regardless of cwd.

### Documentation
- SKILL.md: new "Reading Command Output" section. Agents repeatedly piped CLI
  output through an inline `python3 -c` parser that assumed the success shape;
  on failure the output is `{"error": true, ...}`, so the parser raised a
  `KeyError` that masked the real error message and forced a wasted re-run.
  The section tells agents to run commands bare with `--pretty` and read the
  JSON directly, and documents the per-command response envelopes.
- SKILL.md: "Environment Setup" rewritten to describe the new ancestor-walking
  `.env` discovery and to state that no `cd` is needed.

## [3.1.1] — 2026-05-16

### Fixed
- All five delete commands (`cards delete`, `checklists delete`,
  `tasks delete`, `webhooks delete`, `tokens revoke`) reported a fake
  success when the delete had in fact failed — each discarded the API
  response and printed `{"deleted": true}` unconditionally. They now route
  the request through the new `http.delete_resource()` and exit non-zero
  with an actionable error when the delete does not happen.

### Added
- `http.delete_resource()` and the `KanbanZoneDeleteUnsupportedError`
  exception. When a delete fails, the error message is written for both
  humans and AI agents: it states the record was not deleted, that this is
  a known Kanban Zone server-side bug, that retrying will not help, and that
  the record must be deleted via the Kanban Zone web UI.
- Prominent "delete operations do not work" sections in `README.md` and
  `SKILL.md`; the affected subcommands are flagged inline in the SKILL.md
  command tables.

### Known issues
- Kanban Zone's DELETE endpoints are non-functional via the API regardless of
  request body — a Kanban Zone server-side bug behind their AWS CloudFront /
  API Gateway edge, which strips DELETE request bodies. Until Kanban Zone
  ships a fix, delete records via the Kanban Zone web UI. Reported to
  Kanban Zone 2026-05-16.

## [3.0.0] — 2026-05-11

### Added
- Full coverage of Kanban Zone Public API v1.4: comments, checklists,
  tasks, card share tokens, webhook CRUD + signature verification, eight
  board reports, organization context, card history/metrics, board
  sub-resources (labels, members, custom fields, templates), card delete.
- Grouped CLI surface (`boards`, `cards`, `comments`, `checklists`,
  `tasks`, `webhooks`, `reports`, `tokens`, `org`).
- Bidirectional card-number ↔ ObjectId cache.
- Card ID auto-detection (`--id 42` or `--id 6700aabb...`).
- Offline `webhooks verify-signature` HMAC-SHA1 helper.
- `--no-cache`, `--pretty`, `--api-token`, `--board` global flags.
- Stdlib `unittest` test suite at ≥ 95 % line coverage.
- `Makefile` with `test`, `coverage`, `coverage-html`, `lint`, `clean`.
- `references/migration-from-v2.md`.

### Changed
- Restructured `scripts/kanban_zone_api.py` from monolith to entry script
  + `scripts/kanban_zone/` package with one module per resource.
- Wire calls migrated silently to v1.4 canonical paths
  (`PATCH /cards/{id}`, `POST /checklists`, `POST /comments`,
  `POST /tokens`, `GET /boards/{publicId}`). Deprecated v1.3 paths no
  longer used.
- `User-Agent` header now `kanban-zone-skill/3.0.0`.

### Deprecated
- v2 flat commands (`create-card`, `update-card`, `move-card`,
  `link-card`, `unlink-card`, `search-cards`, `wip-check`, `boards`,
  `board`, `cards`, `card`, `create-cards`) remain as hidden aliases
  but are not shown in `--help`. Use the grouped equivalents documented
  in `references/migration-from-v2.md`.

### Notes
- Cache file is forward-compatible — v2 cache files load cleanly.
- `.env` keys (`KANBAN_ZONE_API_KEY`, `KANBAN_ZONE_BOARD_ID`) unchanged.

## [2.1.0] — 2026-04-16
- HTML table warning added to description-formatting rules. (See git history.)

## [2.0.0] — 2026-04-27
- Rebrand from prior naming to "Kanban Zone"; env vars renamed. (See git history.)
