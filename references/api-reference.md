# Kanban Zone Public API Reference (v1.4)

**Base URL:** `https://integrations.kanbanzone.io/v1/`
**Protocol:** HTTPS only
**API Version:** v1.4 (April 29, 2026)

---

## Authentication

Generate your **Organization API Key** from Kanban Zone:
- **Settings > Organization Settings > Integrations > API Key**
- Direct URL: `https://kanbanzone.io/settings/integrations`

The full key has the shape `accessId:apiKey`. Base64-encode the entire string before use.

```bash
printf 'accessId:apiKey' | base64
```

**Option 1 — Authorization Header (recommended):**
```
Authorization: Basic {base64-encoded-key}
```

**Option 2 — Query Parameter:**
```
?api_token={base64-encoded-key}
```

All API activity performed with your key is your responsibility. Keep it secret; do not share or sublicense it.

---

## Rate Limits

| Plan | Monthly API Calls |
|------|-------------------|
| Free / Basic | Not available |
| Professional | 1,000 / month |
| Enterprise | Unlimited |

Webhooks and Zapier token management require the **Enterprise** plan.

---

## Boards

### GET /boards

List all boards and board metrics within your organization.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `includeArchived` | query | No | boolean | false | Include archived boards in the response |

**Response:** `BoardsOutputModel`

---

### GET /boards/{publicId}

Get a single board with metrics. Canonical replacement for `GET /board/{board}` (deprecated).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |
| `includeColumns` | query | No | boolean | false | Include column details |
| `includeMembers` | query | No | boolean | false | Include board members |
| `includeCustomFields` | query | No | boolean | false | Include custom field definitions |
| `includeLabels` | query | No | boolean | false | Include board labels |

**Response:** `BoardItemOutputModel`

---

### GET /boards/{publicId}/columns

List all columns of a board, sorted by position.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |

**Response:** Array of `ColumnItemOutputModel`

---

### GET /boards/{publicId}/labels

List labels scoped to a board, sorted by position.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |

**Response:** Array of label objects (`{ id, name, color }`)

---

### GET /boards/{publicId}/members

List confirmed members of a board.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |

**Response:** Array of `OrganizationMemberModel`

---

### GET /boards/{publicId}/custom-fields

List custom field definitions registered for a board.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |

**Response:** Array of custom field definition objects

---

### GET /boards/{publicId}/reports/{reportType}

Get a board-level analytics report.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |
| `reportType` | path | **Yes** | string | — | One of: `allocation`, `throughput`, `arrival-rate`, `cycle-time`, `lead-time`, `flow`, `abandoned-effort`, `flow-efficiency` |
| `from` | query | No | string | — | Start date (ISO 8601, e.g. `2026-01-01`) |
| `to` | query | No | string | — | End date (ISO 8601, e.g. `2026-04-01`) |

**Response:** Report object (shape varies by `reportType`)

---

## Cards

### GET /cards

Get cards from a board. Supports pagination and filtering.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `board` | query | **Yes** | string | — | Board public ID |
| `page` | query | No | number | 1 | Page number (1-based) |
| `count` | query | No | number | 100 | Cards per page (max 100) |
| `daysSinceLastUpdate` | query | No | number | — | Filter to cards updated within N days |
| `includeArchived` | query | No | boolean | false | Include archived cards |
| `columns` | query | No | string | — | Comma-separated column IDs to filter by |

**Response:** `CardsOutputModel`

---

### POST /cards

Add one or more cards to a board.

**Request Body:** `CardsInputModel` (required)

**Response:** `CardsAddedOutputModel`

---

### GET /cards/{id}

Get a specific card by its card number (e.g., `872`).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** `CardItemOutputModel`

---

### PATCH /cards/{id}

Update a card. Send only the fields to change. Canonical replacement for `PUT /cards/{id}` (deprecated).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Request Body:** `CardItemInputModel` (partial — only include fields to change)

**Response:** `CardItemOutputModel`

**Note:** For mirrored cards, include `board` (board public ID) in the body to identify which mirror to update.

---

### DELETE /cards/{id}

Soft-delete a card by moving it to the board's archive bucket. For mirror cards, deletes the mirror on the specified board (and flattens the source card back to a regular card if only one mirror remains).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |
| `board` | query | No | string | — | Board public ID. Required when deleting a mirror. |

**Response:** `{ success: boolean }`

---

### POST /cards/{id}/move

Move a card to a different column.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Request Body:** `CardMoveInputModel` (required)

**Response:** `CardItemOutputModel`

**Note:** For mirrored cards, include `board` in the body.

---

### GET /cards/{id}/history

Get the full audit history for a card.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** Array of history event objects

---

### GET /cards/{id}/metrics

Get cycle time and lead time metrics for a card.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** Metrics object with cycle time, lead time, and column dwell times

---

### GET /cards/{id}/comments

List all comments on a card.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** Array of `Comment`

---

### GET /cards/{id}/checklists

List all checklists (and their tasks) for a card, sorted by position.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** Array of `ChecklistModel`

---

### GET /cards/{id}/tokens

List all share tokens assigned to a card.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | number | — | Card number |

**Response:** Array of `CardTokenModel`

---

## Comments

### POST /comments

Create a comment on a card. Canonical replacement for `POST /cards/{id}/comments` (deprecated).

**Request Body:** `CommentCreateInput` (required)

**Response:** `Comment`

---

## Checklists

### POST /checklists

Create a checklist on a card. Optionally seed it with tasks in one call. Canonical replacement for `POST /cards/{id}/checklists` (deprecated).

**Request Body:** `ChecklistCreateInput` (required)

**Response:** `ChecklistModel`

**Note:** The optional `tasks` array creates tasks alongside the checklist. Each task requires `description`. Position is determined by array index; any `position` field in the task objects is ignored.

---

### PATCH /checklists/{id}

Update a checklist (e.g., rename it).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Checklist object ID |

**Request Body:** `ChecklistUpdateInput` (partial)

**Response:** `ChecklistModel`

---

### DELETE /checklists/{id}

Delete a checklist and all its tasks.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Checklist object ID |

**Response:** `ChecklistDeleteResult`

---

## Tasks

### POST /tasks

Create a task inside an existing checklist.

**Request Body:** `TaskCreateInput` (required)

**Response:** `TaskModel`

---

### PATCH /tasks/{id}

Update a task (e.g., mark complete, change description or due date).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Task object ID |

**Request Body:** `TaskUpdateInput` (partial)

**Response:** `TaskModel`

---

### DELETE /tasks/{id}

Delete a task.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Task object ID |

**Response:** `{ success: boolean }`

---

### POST /tasks/{id}/move

Move a task between checklists or reorder within the same checklist.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Task object ID |

**Request Body:** `TaskMoveInput` (required)

**Response:** `TaskModel`

---

## Tokens

Tokens are named share tokens (defined in Organization Settings) that can be assigned to cards to control card visibility and sharing behavior. Requires Enterprise plan.

### POST /tokens

Assign a token to a card. Canonical replacement for `POST /cards/{id}/tokens` (deprecated).

**Request Body:** `TokenCreateInput` (required)

**Response:** `CardTokenModel`

---

### DELETE /tokens/{id}

Revoke (unassign) a token from a card.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Card token object ID (from `CardTokenModel`) |

**Response:** `{ success: boolean }`

---

## Webhooks

Webhooks notify your application when card events occur. Manage webhooks via the API or through **Organization Menu > Integrations > Webhooks**. Requires Enterprise plan.

### GET /webhooks

List all webhooks for a board.

**Response:** Array of `WebhookOutputModel`

---

### POST /webhooks

Create a new webhook.

**Request Body:** `WebhookInputModel` (required)

**Response:** `WebhookOutputModel`

---

### GET /webhooks/{id}

Get details of a specific webhook.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Webhook ID |

**Response:** `WebhookOutputModel`

---

### PUT /webhooks/{id}

Update an existing webhook (e.g., change the destination URL or event).

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Webhook ID |

**Request Body:** `WebhookInputModel` (partial)

**Response:** `WebhookOutputModel`

---

### DELETE /webhooks/{id}

Delete a webhook.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Webhook ID |

**Response:** `{ success: boolean }`

---

### POST /webhooks/{id}/test

Send a synthetic test event to a webhook's configured URL so you can verify your endpoint accepts the payload shape before going live. Requires a webhook signing key to be configured on the organization.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `id` | path | **Yes** | string | — | Webhook ID |

**Response:** `{ success: boolean }`

---

## Reports

Board-level analytics. Report endpoints use the legacy URL pattern `GET /board/{board}/reports/{reportType}`.

### GET /board/{board}/reports/throughput
### GET /board/{board}/reports/allocation
### GET /board/{board}/reports/arrival-rate
### GET /board/{board}/reports/cycle-time
### GET /board/{board}/reports/lead-time
### GET /board/{board}/reports/flow
### GET /board/{board}/reports/abandoned-effort
### GET /board/{board}/reports/flow-efficiency

All report endpoints share the same parameters:

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `board` | path | **Yes** | string | — | Board public ID |
| `from` | query | No | string | — | Start date (ISO 8601) |
| `to` | query | No | string | — | End date (ISO 8601) |

**Preferred alternative:** Use `GET /boards/{publicId}/reports/{reportType}` (same report types, same parameters — see Boards section).

---

## Templates

### GET /templates/{publicId}

List card templates for a board.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `publicId` | path | **Yes** | string | — | Board public ID |

**Response:** Array of template objects (`{ id, name, publicId }`)

**Note:** Template IDs are 8-character, case-sensitive public IDs found in **Board Settings > Card > Templates**. Pass a template's `publicId` as `templateId` in `CardItemInputModel` when creating a card.

---

## Organization

### GET /me

Lightweight credential check. Returns the authenticated organization's name and confirms the API key is valid.

**Response:** `{ success: boolean, name: string }`

---

### GET /organization

Get descriptive information about the authenticated organization (name, plan, AI plan, feature flags). Use the `include*` flags to expand the response with boards, members, and custom fields in a single call. Designed for AI tools and integrations that need to discover everything about the organization at startup.

**Note:** Sensitive credentials (apiKey, webhookKey, Paddle subscription IDs) are never included in the response.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `includeBoards` | query | No | boolean | false | Include the array of boards |
| `includeMembers` | query | No | boolean | false | Include licensed and unlicensed organization members |
| `includeCustomFields` | query | No | boolean | false | Include the organization-level custom field definitions |
| `includeColumns` | query | No | boolean | false | When `includeBoards=true`, also include each board's columns |
| `includeLabels` | query | No | boolean | false | When `includeBoards=true`, also include each board's labels |

**Response:** `OrganizationContextModel`

---

## Data Models

### CardItemInputModel

Used in PATCH /cards/{id} and as the per-card shape inside `CardsInputModel`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `board` | string | No* | Board public ID. *Required for mirror card operations. |
| `columnId` | string | No | Target column ID (from Board Settings > API) |
| `title` | string | No* | Card title. *Required for POST /card (single create). |
| `description` | string | No | Plain text or HTML |
| `templateId` | string | No | 8-char card template public ID (case-sensitive) |
| `blocked` | boolean | No | Whether the card is blocked |
| `blockedBy` | string | No | Email of the member blocking this card |
| `blockedReason` | string | No | Human-readable reason for the block |
| `dueAt` | string | No | Due date: `MM/DD/YYYY` or ISO 8601 |
| `owner` | string | No | Owner's email address |
| `priority` | string | No | `"1"` (highest) through `"4"` (lowest) |
| `label` | string | No | Label name (must exist on the board) |
| `size` | string | No | `"S"`, `"M"`, `"L"`, or `"XL"` |
| `watchers` | string[] | No | Array of watcher email addresses |
| `customFields` | object[] | No | `[{"label": "Field Name", "value": "..."}]` |
| `links` | object | No | Card/URL links; see Links Sub-Schema below |

### CardInputModel (POST /card — legacy single-card create)

Extends `CardItemInputModel` with:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `board` | string | **Yes** | — | Board public ID |
| `title` | string | **Yes** | — | Card title |
| `addToTop` | boolean | No | false | Add to top of column instead of bottom |

### CardsInputModel (POST /cards)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `board` | string | **Yes** | — | Board public ID |
| `cards` | CardItemInputModel[] | **Yes** | — | Array of card objects to create |
| `addToTop` | boolean | No | false | Position for all cards in the batch |

### CardMoveInputModel

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `columnId` | string | **Yes** | Target column ID (from Board Settings > API) |
| `board` | string | No | Board public ID. Required for mirrored cards. |
| `addToTop` | boolean | No | Place at top of column (default: bottom) |

### Links Sub-Schema (v1.3+)

Passed as the `links` field in `CardItemInputModel`:

```json
{
  "links": {
    "add": [
      { "card": 123, "type": "related" },
      { "card": 456, "type": "parent" },
      { "url": "https://example.com", "title": "Example", "type": "external" }
    ],
    "remove": [
      { "card": 789 },
      { "url": "https://old-link.com" }
    ]
  }
}
```

Valid `type` values: `"related"`, `"parent"`, `"child"`, `"external"`.

---

### CardItemOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `boardTitle` | string | Board name |
| `boardPublicId` | string | Board public ID |
| `columnId` | string | Current column ID |
| `columnTitle` | string | Current column name |
| `columnState` | string | Column state (see Column States section) |
| `number` | integer | Card number (unique within the board) |
| `title` | string | Card title |
| `description` | string | Card description (may be HTML) |
| `blocked` | boolean | Whether the card is blocked |
| `blockedBy` | string | Email of the blocking member |
| `blockedReason` | string | Reason for the block |
| `dueAt` | string | Due date (ISO 8601) |
| `owner` | string | Owner email address |
| `priority` | string | Priority level (`"1"`–`"4"`) |
| `label` | string | Label name |
| `size` | string | Card size (`"S"`, `"M"`, `"L"`, `"XL"`) |
| `watchers` | string[] | Watcher email addresses |
| `lastActionAt` | string | Last update timestamp (ISO 8601) |
| `lastActionBy` | string | Email of last updater |
| `archivedAt` | string | Archive timestamp (ISO 8601), or null |
| `doneAt` | string | First-time-done timestamp (ISO 8601), or null |
| `createdAt` | string | Creation timestamp (ISO 8601) |
| `customFields` | object[] | `[{"label": "...", "value": "..."}]` |
| `links` | object | Card-to-card and external URL links (v1.3+) |

### CardsOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Number of cards in this page |
| `totalAvailable` | integer | Total matching cards across all pages |
| `hasMore` | boolean | Whether additional pages exist |
| `cards` | CardItemOutputModel[] | Card objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

### CardsAddedOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `cardsAdded` | integer | Number of cards successfully created |
| `cards` | CardItemOutputModel[] | Created card objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

---

### BoardItemOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `publicId` | string | Board public ID |
| `name` | string | Board name |
| `isArchived` | boolean | Whether the board is archived |
| `activeCardsCount` | number | Count of active (non-archived) cards |
| `archivedCardsCount` | number | Count of archived cards |
| `backlogCardsCount` | number | Count of cards in Backlog state |
| `blockedCardsCount` | number | Count of blocked cards |
| `overdueCardsCount` | number | Count of overdue cards |
| `adminsCount` | number | Number of board administrators |
| `collaboratorsCount` | number | Number of collaborators |
| `subscribersCount` | number | Number of subscribers |
| `columns` | ColumnItemOutputModel[] | Columns (present when `includeColumns=true`) |
| `members` | OrganizationMemberModel[] | Members (present when `includeMembers=true`) |
| `labels` | object[] | Labels (present when `includeLabels=true`) |
| `customFields` | object[] | Custom fields (present when `includeCustomFields=true`) |

### BoardsOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Number of boards in the response |
| `boards` | BoardItemOutputModel[] | Board objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

### BoardInputModel

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `board` | string | **Yes** | Board public ID |

### ColumnItemOutputModel (v1.3+)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Column object ID |
| `parent` | string | Parent column ID (null if root column) |
| `parentTitle` | string | Parent column name |
| `title` | string | Column name |
| `type` | string | `"CARD"` (leaf) or `"PARENT"` (swimlane/group) |
| `columnState` | string | Column state (see Column States section) |
| `minWIP` | number | Minimum WIP limit (0 = none) |
| `maxWIP` | number | Maximum WIP limit (0 = none) |
| `explicitAgreement` | string | Entry agreement text for the column |

---

### ChecklistModel

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Checklist object ID |
| `card` | string | Parent card object ID |
| `title` | string | Checklist title |
| `position` | number | Sort order within the card |
| `tasks` | TaskModel[] | Tasks in this checklist (sorted by position) |

### ChecklistCreateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `card` | string | **Yes** | Card object ID (not card number) |
| `title` | string | **Yes** | Checklist title |
| `tasks` | object[] | No | Seed tasks: `[{"description": "..."}]`. Position from array index. |

### ChecklistUpdateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | No | New checklist title |

### ChecklistDeleteResult

| Field | Type | Description |
|-------|------|-------------|
| `deleted` | boolean | Whether the checklist was deleted |
| `id` | string | ID of the deleted checklist |

---

### TaskModel

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Task object ID |
| `checklist` | string | Parent checklist object ID |
| `description` | string | Task text |
| `completed` | boolean | Whether the task is completed |
| `position` | number | Sort order within the checklist |
| `dueAt` | string | Due date (ISO 8601), or null |
| `completedAt` | string | Completion timestamp (ISO 8601), or null |

### TaskCreateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `checklist` | string | **Yes** | Checklist object ID |
| `description` | string | **Yes** | Task text |
| `position` | number | No | Sort position within the checklist |
| `dueAt` | string | No | Due date (ISO 8601) |

### TaskUpdateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Updated task text |
| `completed` | boolean | No | Mark complete (`true`) or incomplete (`false`) |
| `dueAt` | string | No | Updated due date (ISO 8601) |

### TaskMoveInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `checklistFrom` | string | **Yes** | Source checklist object ID |
| `checklistTo` | string | **Yes** | Destination checklist object ID |
| `position` | number | **Yes** | Target position in the destination checklist (0-based) |

---

### CommentCreateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `card` | string | **Yes** | Card object ID (not card number) |
| `text` | string | **Yes** | Comment text (plain text) |

### CommentInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `card` | string | **Yes** | Card object ID |
| `text` | string | **Yes** | Comment text |

### Comment

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Comment object ID |
| `card` | string | Parent card object ID |
| `text` | string | Comment text |
| `author` | string | Author email address |
| `createdAt` | string | Creation timestamp (ISO 8601) |
| `reactions` | Reaction[] | Emoji reactions on this comment |

### Reaction

| Field | Type | Description |
|-------|------|-------------|
| `emoji` | string | Emoji character or short code |
| `count` | number | Number of users who reacted with this emoji |
| `users` | string[] | Email addresses of reacting users |

---

### TokenCreateInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `card` | string | **Yes** | Card object ID |
| `tokenId` | string | **Yes** | Token definition ID (from Organization Settings) |
| `board` | string | **Yes** | Board object ID (not public ID) |

### CardTokenModel

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Card token assignment object ID (use for DELETE /tokens/{id}) |
| `card` | string | Card object ID |
| `tokenId` | string | Token definition ID |
| `tokenName` | string | Human-readable token name |
| `assignedAt` | string | Assignment timestamp (ISO 8601) |

---

### WebhookInputModel

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `board` | string | **Yes** | Board public ID |
| `event` | string | **Yes** | One of: `CARD_CREATED`, `CARD_MOVED`, `CARD_UPDATED` |
| `url` | string | **Yes** | Destination HTTPS URL to receive POST payloads |

### WebhookOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Webhook object ID |
| `board` | string | Board public ID |
| `event` | string | Subscribed event type |
| `url` | string | Destination URL |
| `createdAt` | string | Creation timestamp (ISO 8601) |

---

### OrganizationContextModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Organization name |
| `plan` | string | Subscription plan name |
| `aiPlan` | string | AI add-on plan name (if any) |
| `features` | object | Feature flags enabled for this organization |
| `boards` | BoardItemOutputModel[] | Boards (present when `includeBoards=true`) |
| `members` | OrganizationMemberModel[] | Members (present when `includeMembers=true`) |
| `customFields` | object[] | Custom field definitions (present when `includeCustomFields=true`) |

### OrganizationMemberModel

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Member's email address |
| `name` | string | Member's display name |
| `licensed` | boolean | Whether the member holds a paid license |
| `role` | string | Organization role (e.g., `"admin"`, `"member"`) |

---

## Webhook Events and Signature Verification

### Supported Events

| Event | Fires when |
|-------|------------|
| `CARD_CREATED` | A new card is created on a board |
| `CARD_MOVED` | A card moves from one column to another |
| `CARD_UPDATED` | An existing card's fields are edited |

### Payload Envelope

Every webhook delivery is a `POST` with `Content-Type: application/json` and this envelope:

```json
{
  "notification": {
    "type": "CARD_CREATED",
    "hookDateTime": "2026-04-30T18:18:09.750Z",
    "payload": {
      "CardItem": { }
    }
  }
}
```

- `notification.type` — one of the event names above
- `notification.hookDateTime` — ISO 8601 timestamp of the event
- `notification.payload.CardItem` — card data matching `CardItemOutputModel`

### Signature Verification (HMAC-SHA1)

Always verify the signature before processing a webhook payload. Generate a **Webhook Key** in Kanban Zone Settings > Integrations > Webhook Key; Kanban Zone signs every delivery with HMAC-SHA1 using that key.

The signature arrives in the `X-KanbanZone-Signature` request header. Re-compute it on your side and compare — reject the request if they do not match.

```javascript
// Verify a Kanban Zone webhook payload signature (Node.js)
const crypto = require('crypto');

// Your Webhook Key from Settings → Integrations → Webhook Key
const secretKey = 'KeyGeneratedFromKanbanZone';

// HMAC-SHA1 over the serialized payload object
const myHash = crypto.createHmac('sha1', secretKey)
    .update(JSON.stringify(req.body.payload))
    .digest('hex');

const webhookSignature = req.headers['x-kanbanzone-signature'];

if (webhookSignature === myHash) {
    // Verified — request is from Kanban Zone
} else {
    // Signature mismatch — reject the request
}
```

**Important:** The HMAC input is `JSON.stringify(req.body.payload)` — the `payload` object from inside `notification`, not the full envelope.

---

## Deprecated Endpoints

These paths still work but will be removed in a future major version. Migrate to the canonical replacements.

| Deprecated Path | Canonical Replacement |
|-----------------|-----------------------|
| `PUT /card/{id}` | `PATCH /cards/{id}` |
| `GET /board/{board}` | `GET /boards/{publicId}` |
| `POST /cards/{id}/checklists` | `POST /checklists` |
| `POST /cards/{id}/comments` | `POST /comments` |
| `POST /cards/{id}/tokens` | `POST /tokens` |

---

## Column States

| State | Description |
|-------|-------------|
| `Backlog` | Pre-commitment items not yet pulled into active flow |
| `To Do` | Committed work ready to start |
| `Buffer` | Queue between stages (handoff or wait state) |
| `In Progress` | Currently being actively worked on |
| `Done` | Work completed within this stage |
| `Archive` | Historical items removed from the active board |
| `None` | No state assigned to this column |

Column IDs are found in **Board Settings > API** or **Organization Settings > Integrations > API**.

---

## Pagination

`GET /cards` supports cursor-free page-based pagination.

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | number | 1 | — | 1-based page number |
| `count` | number | 100 | 100 | Cards per page |

Response fields for pagination:

| Field | Type | Description |
|-------|------|-------------|
| `hasMore` | boolean | `true` if additional pages exist |
| `totalAvailable` | integer | Total matching cards across all pages |
| `count` | integer | Cards in this page |

**Example:** to retrieve page 3 with 50 cards per page:
```
GET /cards?board=BOARDID&page=3&count=50
```

---

## Notes

- **Column IDs:** Found in Board Settings > API, or Organization Settings > Integrations > API.
- **Template IDs:** 8-character, case-sensitive public IDs from Board Settings > Card > Templates.
- **Mirror cards:** Include `board` (board public ID) in request body when updating, moving, or deleting.
- **Description field:** Accepts plain text or HTML; output may be HTML.
- **Date input:** `MM/DD/YYYY` or ISO 8601 accepted; all output is ISO 8601.
- **Card object ID vs. card number:** Most body fields accept the card's internal object ID (a MongoDB-style hex string). Path parameters like `/cards/{id}` use the card's human-readable number (e.g., `872`).
- **Checklist/Task IDs:** Internal object IDs — use the `id` field from the respective output models.
- **Webhooks and Tokens:** Require the Enterprise plan.
