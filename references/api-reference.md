# Kanban Zone Public API Reference (v1.3)

**Base URL:** `https://integrations.kanbanzone.io/v1/`
**Protocol:** HTTPS only

## Authentication

Generate your **Organization API Key** from:
- **Settings > Organization Settings > Integrations > API Key**
- Direct URL: `https://kanbanzone.io/settings/integrations`

The API key must be **Base64-encoded** before use.

**Option 1 — Authorization Header (recommended):**
```
Authorization: Basic {base64-encoded-key}
```

**Option 2 — Query Parameter:**
```
?api_token={base64-encoded-key}
```

## Rate Limits

| Plan | Monthly API Calls |
|------|-------------------|
| Free/Basic | Not available |
| Professional | 1,000/month |
| Enterprise | Unlimited |

Webhooks and Zapier tokens require Enterprise plan.

---

## Boards

### GET /boards

Get all boards and board metrics.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `includeArchived` | query | No | boolean | false | Include archived boards |
| `includeColumns` | query | No | boolean | false | Include column details (v1.3+) |

**Response:** `BoardsOutputModel`

### GET /board/{board}

Get a specific board with metrics.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `board` | path | **Yes** | string | — | Board public ID |
| `includeColumns` | query | No | boolean | false | Include column details (v1.3+) |

**Response:** `BoardsOutputModel`

---

## Cards

### GET /card

Retrieve a specific card by board and card number.

| Parameter | In | Required | Type | Description |
|-----------|----|----------|------|-------------|
| `board` | query | **Yes** | string | Board public ID |
| `number` | query | **Yes** | string | Card number |

**Response:** `CardsOutputModel`

### GET /cards

Get cards from a board. Supports pagination and filtering.

| Parameter | In | Required | Type | Default | Description |
|-----------|----|----------|------|---------|-------------|
| `board` | query | **Yes** | string | — | Board public ID |
| `page` | query | No | number | 1 | Page number |
| `count` | query | No | number | 100 | Cards per page (max 100) |
| `daysSinceLastUpdate` | query | No | number | — | Filter by recency |
| `includeArchived` | query | No | boolean | false | Include archived cards |

**Response:** `CardsOutputModel`

### POST /card

Add a single card to a board.

**Request Body:** `CardInputModel` (required)

**Response:** `CardsAddedOutputModel`

### POST /cards

Add multiple cards to a board.

**Request Body:** `CardsInputModel` (required)

**Response:** `CardsAddedOutputModel`

### PUT /card/{id}

Update a card. Only include fields to change.

| Parameter | In | Required | Type | Description |
|-----------|----|----------|------|-------------|
| `id` | path | **Yes** | number | Card number |

**Request Body:** `CardItemInputModel` (partial)

**Response:** `CardItemOutputModel`

For mirrored cards, include `board` in the body.

### POST /card/{id}/move

Move a card to a different column.

| Parameter | In | Required | Type | Description |
|-----------|----|----------|------|-------------|
| `id` | path | **Yes** | number | Card number |

**Request Body:** `CardMoveInputModel` (required)

**Response:** `CardItemOutputModel`

For mirrored cards, include `board` in the body.

---

## Data Models

### CardItemInputModel

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `board` | string | No* | Board public ID. *Required for mirror card ops. |
| `columnId` | string | No | Target column ID (from Board Settings > API) |
| `title` | string | **Yes** | Card title |
| `description` | string | No | Plain text or HTML |
| `templateId` | string | No | 8-char card template public ID (case-sensitive) |
| `blocked` | boolean | No | Whether card is blocked |
| `blockedBy` | string | No | Email of blocking member |
| `blockedReason` | string | No | Reason for blocking |
| `dueAt` | string | No | Due date: `MM/DD/YYYY` or ISO 8601 |
| `owner` | string | No | Owner email |
| `priority` | string | No | `"1"`, `"2"`, `"3"`, or `"4"` |
| `label` | string | No | Label name |
| `size` | string | No | `"S"`, `"M"`, `"L"`, or `"XL"` |
| `watchers` | string[] | No | Watcher emails |
| `customFields` | object[] | No | `[{"label": "...", "value": "..."}]` |
| `links` | object | No | (v1.3+) See Links sub-schema |

### CardInputModel (POST /card)

Extends `CardItemInputModel` with:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `board` | string | **Yes** | — | Board public ID |
| `addToTop` | boolean | No | false | Add to top of column |

### CardsInputModel (POST /cards)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `board` | string | **Yes** | — | Board public ID |
| `addToTop` | boolean | No | false | Position for all cards |
| `cards` | CardItemInputModel[] | **Yes** | — | Array of cards |

### CardMoveInputModel

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `columnId` | string | **Yes** | Target column ID |
| `board` | string | No | Required for mirrored cards |

### Links Sub-Schema (v1.3+)

```json
{
  "links": {
    "add": [
      { "card": 123, "type": "related" },
      { "url": "https://example.com", "title": "Example", "type": "external" }
    ],
    "remove": [
      { "card": 456 },
      { "url": "https://old-link.com" }
    ]
  }
}
```

---

## Response Models

### CardItemOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `boardTitle` | string | Board name |
| `boardPublicId` | string | Board public ID |
| `columnId` | string | Current column ID |
| `columnTitle` | string | Current column name |
| `columnState` | string | Column state (see below) |
| `number` | integer | Card number |
| `title` | string | Card title |
| `description` | string | Card description |
| `blocked` | boolean | Whether blocked |
| `blockedBy` | string | Blocking member email |
| `blockedReason` | string | Block reason |
| `dueAt` | string | Due date (ISO 8601) |
| `owner` | string | Owner email |
| `priority` | string | Priority level |
| `label` | string | Label name |
| `size` | string | Card size |
| `watchers` | string[] | Watcher emails |
| `lastActionAt` | string | Last update (ISO 8601) |
| `lastActionBy` | string | Last updater email |
| `archivedAt` | string | Archive timestamp |
| `doneAt` | string | First Done entry timestamp |
| `createdAt` | string | Creation timestamp |
| `customFields` | object[] | Custom field values |
| `links` | object | (v1.3+) Card/external links |

### CardsOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Cards in this response |
| `totalAvailable` | integer | Total matching cards |
| `hasMore` | boolean | More pages available |
| `cards` | CardItemOutputModel[] | Card objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

### CardsAddedOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `cardsAdded` | integer | Cards successfully added |
| `cards` | CardItemOutputModel[] | Created card objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

### BoardItemOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `publicId` | string | Board public ID |
| `name` | string | Board name |
| `isArchived` | boolean | Whether archived |
| `activeCardsCount` | number | Active cards |
| `archivedCardsCount` | number | Archived cards |
| `backlogCardsCount` | number | Backlog cards |
| `blockedCardsCount` | number | Blocked cards |
| `overdueCardsCount` | number | Overdue cards |
| `adminsCount` | number | Administrators |
| `collaboratorsCount` | number | Collaborators |
| `subscribersCount` | number | Subscribers |
| `columns` | ColumnItemOutputModel[] | (v1.3+, when `includeColumns=true`) |

### BoardsOutputModel

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Boards in response |
| `boards` | BoardItemOutputModel[] | Board objects |
| `errors` | object | `{"error": bool, "errors": ["..."]}` |

### ColumnItemOutputModel (v1.3+)

| Field | Type | Description |
|-------|------|-------------|
| `boardTitle` | string | Column ID |
| `parent` | string | Parent column ID (null if root) |
| `parentTitle` | string | Parent column name |
| `title` | string | Column name |
| `type` | string | `CARD` or `PARENT` |
| `columnState` | string | Column state |
| `minWIP` | number | Min WIP limit |
| `maxWIP` | number | Max WIP limit |
| `explicitAgreement` | string | Column entry agreement text |

---

## Column States

| State | Description |
|-------|-------------|
| `Backlog` | Pre-commitment items |
| `To Do` | Committed, ready to start |
| `Buffer` | Queue between stages |
| `In Progress` | Currently being worked on |
| `Done` | Completed |
| `Archive` | Historical items |
| `None` | No state assigned |

---

## Pagination

- `GET /cards` supports `page` and `count` query parameters
- Max `count`: 100 (default: 100)
- Default `page`: 1
- Check `hasMore` to determine if more pages exist
- Use `totalAvailable` for total count

---

## Webhooks (UI-configured, not API-managed)

Configure via **Organization Menu > Integrations > Webhooks tab**.

- Optional webhook key for payload validation
- One or many webhooks per board
- Triggers: **Card Created**, **Card Moved**
- Payload: JSON POST with card details matching `CardItemOutputModel`
- Enterprise plan required

---

## Notes

- **Column IDs**: Found in Board Settings > API, or Organization Settings > Integrations > API
- **Template IDs**: 8-char case-sensitive IDs from Board Settings > Card > Templates
- **Mirror cards**: Require `board` in update/move request bodies
- **Description**: Accepts plain text or HTML
- **Date input**: `MM/DD/YYYY` or ISO 8601; output is always ISO 8601
- **Links** (v1.3+): Supports card-to-card and external URL links
