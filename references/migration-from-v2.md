# Migrating from Kanban Zone Skill v2 to v3

v3 reorganises the CLI into resource groups (`boards`, `cards`, `comments`,
...) and migrates wire calls to v1.4 canonical endpoints. **All v2 commands
keep working** as hidden aliases for back-compat.

## Hidden flat-command alias map

| v2 flat command   | v3 grouped equivalent      |
|-------------------|----------------------------|
| `boards`          | `boards list`              |
| `board`           | `boards get`               |
| `cards`           | `cards list`               |
| `card --number N` | `cards get --id N`         |
| `create-card`     | `cards create`             |
| `create-cards`    | `cards create-bulk`        |
| `update-card`     | `cards update`             |
| `move-card`       | `cards move`               |
| `link-card`       | `cards links-add`          |
| `unlink-card`     | `cards links-remove`       |
| `search-cards`    | `cards search`             |
| `wip-check`       | `cards wip-check`          |

## Silent endpoint migration

| v2 wire call (deprecated)        | v3 wire call (canonical)             |
|----------------------------------|--------------------------------------|
| `PUT /card/{id}`                 | `PATCH /cards/{id}`                  |
| `POST /cards/{id}/checklists`    | `POST /checklists`                   |
| `POST /cards/{id}/comments`      | `POST /comments`                     |
| `POST /cards/{id}/tokens`        | `POST /tokens`                       |
| `GET /board/{board}`             | `GET /boards/{publicId}`             |

The legacy aliases above call the new endpoints transparently. Output JSON
shape is unchanged; only the wire path differs.

## Cache schema migration

v2 cache files persist as-is. New keys (`cards.byNumber`, `cards.byObjectId`)
are added on first write that produces them. Nothing to do manually.

## When to update your scripts

You don't have to. Aliases will keep working. But:
- New code should use the grouped surface (it's the only thing in `--help`).
- New endpoints (comments, checklists, tasks, webhooks CRUD, reports, etc.)
  are only available through the grouped surface.

## When the aliases will go away

No deprecation date is currently set. The aliases will stay as long as Kanban
Zone Public API v1.4 honours its deprecated paths.
