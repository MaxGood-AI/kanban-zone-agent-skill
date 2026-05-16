# Changelog

All notable changes to the Kanban Zone skill. Versioning follows SemVer.

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
