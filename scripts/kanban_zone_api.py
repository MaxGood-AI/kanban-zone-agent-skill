#!/usr/bin/env python3
"""Kanban Zone API CLI client.

Self-contained client using only Python standard library.
All output is JSON.

Environment variables (auto-loaded from .env if not in environment):
    KANBAN_ZONE_API_KEY  — Raw API key (Base64-encoded automatically)
    KANBAN_ZONE_BOARD_ID — Default board public ID
"""

import argparse
import base64
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://integrations.kanbanzone.io/v1"

_env_loaded = False


def _load_env_file():
    """Load KANBAN_ZONE_* variables from .env if not already in the environment."""
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True

    if os.environ.get("KANBAN_ZONE_API_KEY"):
        return

    candidates = []
    seen = set()

    # Search upward from both the current working directory and the skill repo.
    # This keeps the CLI working when it is invoked from the workspace root,
    # the installed skill directory, or the source repo.
    search_roots = [
        Path.cwd(),
        Path(__file__).resolve().parents[1],
    ]
    for root in search_roots:
        current = root
        while True:
            candidate = current / ".env"
            candidate_str = str(candidate)
            if candidate_str not in seen:
                candidates.append(candidate_str)
                seen.add(candidate_str)
            if current.parent == current:
                break
            current = current.parent

    for path in candidates:
        if os.path.isfile(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key.startswith("KANBAN_ZONE_"):
                        os.environ.setdefault(key, value)
            break


def get_api_key():
    _load_env_file()
    raw = os.environ.get("KANBAN_ZONE_API_KEY")
    if not raw:
        error_exit("KANBAN_ZONE_API_KEY environment variable is not set")
    return base64.b64encode(raw.encode()).decode()


def get_default_board():
    _load_env_file()
    return os.environ.get("KANBAN_ZONE_BOARD_ID")


def require_board(args):
    board = args.board or get_default_board()
    if not board:
        error_exit("Board ID required. Use --board or set KANBAN_ZONE_BOARD_ID")
    return board


def error_exit(message):
    json.dump({"error": True, "message": message}, sys.stdout, indent=2)
    print()
    sys.exit(1)


def api_request(method, path, params=None, body=None):
    encoded_key = get_api_key()
    url = f"{BASE_URL}{path}"

    if params:
        filtered = {k: v for k, v in params.items() if v is not None}
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {encoded_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"error": True, "message": raw.strip() or "Empty response"}
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        return {"error": True, "status": e.code, "message": e.reason, "body": body_text}
    except urllib.error.URLError as e:
        return {"error": True, "message": str(e.reason)}


def output(data):
    json.dump(data, sys.stdout, indent=2)
    print()


def parse_custom_fields(raw_list):
    """Parse ["Label=Value", ...] into [{"label": "...", "value": "..."}, ...]."""
    fields = []
    for item in raw_list:
        if "=" not in item:
            error_exit(f"Invalid custom field format: '{item}'. Use 'Label=Value'.")
        label, value = item.split("=", 1)
        fields.append({"label": label.strip(), "value": value.strip()})
    return fields


def fetch_all_cards(board, include_archived=False):
    """Fetch all cards from a board, handling pagination."""
    params = {"board": board, "count": 100}
    if include_archived:
        params["includeArchived"] = "true"
    cards_data = api_request("GET", "/cards", params=params)
    if cards_data.get("error"):
        return cards_data
    all_cards = cards_data.get("cards", [])
    page = 2
    while cards_data.get("hasMore"):
        params["page"] = page
        cards_data = api_request("GET", "/cards", params=params)
        if cards_data.get("error"):
            break
        all_cards.extend(cards_data.get("cards", []))
        page += 1
    return all_cards


def get_card_field(card, field):
    """Get a field from a card, checking both top-level and nested CardItem."""
    if field in card:
        return card[field]
    card_item = card.get("CardItem", {})
    return card_item.get(field)


def filter_cards(cards, label=None, owner=None, column=None, priority=None,
                 blocked=False, query=None):
    """Apply client-side filters to a list of cards."""
    result = []
    for card in cards:
        if label and (get_card_field(card, "label") or "").lower() != label.lower():
            continue
        if owner and (get_card_field(card, "owner") or "").lower() != owner.lower():
            continue
        if column and (get_card_field(card, "columnTitle") or "").lower() != column.lower():
            continue
        if priority and str(get_card_field(card, "priority") or "") != str(priority):
            continue
        if blocked and not get_card_field(card, "blocked"):
            continue
        if query:
            q = query.lower()
            title = (get_card_field(card, "title") or "").lower()
            desc = (get_card_field(card, "description") or "").lower()
            if q not in title and q not in desc:
                continue
        result.append(card)
    return result


# ── Subcommand handlers ──────────────────────────────────────────────


def cmd_boards(args):
    params = {}
    if args.include_archived:
        params["includeArchived"] = "true"
    if args.include_columns:
        params["includeColumns"] = "true"
    output(api_request("GET", "/boards", params=params))


def cmd_board(args):
    board = require_board(args)
    params = {}
    if args.include_columns:
        params["includeColumns"] = "true"
    output(api_request("GET", f"/board/{board}", params=params))


def cmd_cards(args):
    board = require_board(args)
    has_filters = (args.label or args.owner or args.column or args.priority
                   or args.blocked or args.query)

    if has_filters:
        all_cards = fetch_all_cards(board, args.include_archived)
        if isinstance(all_cards, dict) and all_cards.get("error"):
            output(all_cards)
            return
        filtered = filter_cards(
            all_cards, label=args.label, owner=args.owner,
            column=args.column, priority=args.priority,
            blocked=args.blocked, query=args.query,
        )
        output({
            "count": len(filtered),
            "totalAvailable": len(filtered),
            "cards": filtered,
            "hasMore": False,
        })
    else:
        params = {"board": board, "page": args.page, "count": args.count}
        if args.days_since_update is not None:
            params["daysSinceLastUpdate"] = args.days_since_update
        if args.include_archived:
            params["includeArchived"] = "true"
        output(api_request("GET", "/cards", params=params))


def cmd_card(args):
    board = require_board(args)
    params = {"board": board, "number": args.number}
    output(api_request("GET", "/card", params=params))


def read_file_arg(path):
    """Read content from a file path, stripping one trailing newline if present."""
    with open(path, "r") as f:
        content = f.read()
    if content.endswith("\n"):
        content = content[:-1]
    return content


def cmd_create_card(args):
    board = require_board(args)
    body = {"board": board, "title": args.title}
    if args.column_id:
        body["columnId"] = args.column_id
    description = args.description
    if args.description_file:
        description = read_file_arg(args.description_file)
    if description:
        body["description"] = description
    if args.owner:
        body["owner"] = args.owner
    if args.priority:
        body["priority"] = args.priority
    if args.label:
        body["label"] = args.label
    if args.size:
        body["size"] = args.size
    if args.due:
        body["dueAt"] = args.due
    if args.template_id:
        body["templateId"] = args.template_id
    if args.add_to_top:
        body["addToTop"] = True
    if args.watcher:
        body["watchers"] = args.watcher
    if args.custom_field:
        body["customFields"] = parse_custom_fields(args.custom_field)
    output(api_request("POST", "/card", body=body))


def cmd_create_cards(args):
    with open(args.file, "r") as f:
        data = json.load(f)
    if "board" not in data:
        board = require_board(args)
        data["board"] = board
    output(api_request("POST", "/cards", body=data))


def cmd_update_card(args):
    body = {}
    if args.title:
        body["title"] = args.title
    description = args.description
    if args.description_file:
        description = read_file_arg(args.description_file)
    if description:
        body["description"] = description
    if args.column_id:
        body["columnId"] = args.column_id
    if args.owner:
        body["owner"] = args.owner
    if args.priority:
        body["priority"] = args.priority
    if args.label:
        body["label"] = args.label
    if args.size:
        body["size"] = args.size
    if args.due:
        body["dueAt"] = args.due
    if args.blocked is not None:
        body["blocked"] = args.blocked.lower() == "true"
    if args.blocked_by:
        body["blockedBy"] = args.blocked_by
    if args.blocked_reason:
        body["blockedReason"] = args.blocked_reason
    if args.mirror_board:
        body["board"] = args.mirror_board
    if args.watcher:
        body["watchers"] = args.watcher
    if args.custom_field:
        body["customFields"] = parse_custom_fields(args.custom_field)
    if not body:
        error_exit("No fields to update. Provide at least one field flag.")
    output(api_request("PUT", f"/card/{args.id}", body=body))


def cmd_move_card(args):
    body = {"columnId": args.column_id}
    if args.mirror_board:
        body["board"] = args.mirror_board
    output(api_request("POST", f"/card/{args.id}/move", body=body))


def cmd_link_card(args):
    link = {}
    if args.card:
        link["card"] = args.card
        link["type"] = args.type or "related"
    elif args.url:
        link["url"] = args.url
        link["type"] = args.type or "external"
        if args.title:
            link["title"] = args.title
    else:
        error_exit("Provide either --card or --url to link.")

    body = {"links": {"add": [link]}}
    if args.mirror_board:
        body["board"] = args.mirror_board
    output(api_request("PUT", f"/card/{args.id}", body=body))


def cmd_unlink_card(args):
    link = {}
    if args.card:
        link["card"] = args.card
    elif args.url:
        link["url"] = args.url
    else:
        error_exit("Provide either --card or --url to unlink.")

    body = {"links": {"remove": [link]}}
    if args.mirror_board:
        body["board"] = args.mirror_board
    output(api_request("PUT", f"/card/{args.id}", body=body))


def cmd_search_cards(args):
    if not args.query and not (args.label or args.owner or args.priority or args.blocked):
        error_exit("Provide --query and/or filter flags (--label, --owner, --priority, --blocked).")

    boards_data = api_request("GET", "/boards")
    if boards_data.get("error"):
        output(boards_data)
        return

    all_results = []
    for board_item in boards_data.get("boards", []):
        bi = board_item.get("BoardItem", board_item)
        board_id = bi.get("publicId")
        if bi.get("isArchived"):
            continue
        cards = fetch_all_cards(board_id, include_archived=args.include_archived)
        if isinstance(cards, dict) and cards.get("error"):
            continue
        filtered = filter_cards(
            cards, label=args.label, owner=args.owner,
            priority=args.priority, blocked=args.blocked,
            query=args.query,
        )
        all_results.extend(filtered)

    output({
        "count": len(all_results),
        "cards": all_results,
    })


def cmd_wip_check(args):
    board = require_board(args)
    board_data = api_request("GET", f"/board/{board}", params={"includeColumns": "true"})

    if board_data.get("error"):
        output(board_data)
        return

    all_cards = fetch_all_cards(board)
    if isinstance(all_cards, dict) and all_cards.get("error"):
        output(all_cards)
        return

    # Count cards per column
    col_counts = {}
    for card in all_cards:
        cid = get_card_field(card, "columnId")
        if cid:
            col_counts[cid] = col_counts.get(cid, 0) + 1

    # Build WIP report
    boards = board_data.get("boards", [])
    columns = []
    if boards:
        bi = boards[0].get("BoardItem", boards[0])
        columns = bi.get("columns", [])

    report = []
    for col_wrapper in columns:
        col = col_wrapper.get("ColumnItem", col_wrapper)
        if col.get("type") != "CARD":
            continue
        col_id = col.get("columnId", col.get("boardTitle"))
        current = col_counts.get(col_id, 0)
        min_wip = col.get("minWIP")
        max_wip = col.get("maxWIP")
        violations = []
        if max_wip and current > max_wip:
            violations.append(f"over max ({current}/{max_wip})")
        if min_wip and current < min_wip:
            violations.append(f"under min ({current}/{min_wip})")
        report.append({
            "columnId": col_id,
            "columnTitle": col.get("title"),
            "columnState": col.get("columnState"),
            "currentCards": current,
            "minWIP": min_wip,
            "maxWIP": max_wip,
            "violations": violations,
        })

    output({"board": board, "columns": report})


# ── CLI setup ─────────────────────────────────────────────────────────


def add_filter_args(parser):
    """Add common card filter arguments to a subparser."""
    parser.add_argument("--label", help="Filter by label name (case-insensitive)")
    parser.add_argument("--owner", help="Filter by owner email (case-insensitive)")
    parser.add_argument("--column", help="Filter by column title (case-insensitive)")
    parser.add_argument("--priority", help="Filter by priority level")
    parser.add_argument("--blocked", action="store_true", help="Show only blocked cards")
    parser.add_argument("--query", help="Search title and description (case-insensitive)")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="kanban_zone_api",
        description="Kanban Zone API CLI client. All output is JSON.",
    )
    parser.add_argument("--board", help="Board public ID (overrides KANBAN_ZONE_BOARD_ID)")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # boards
    p = sub.add_parser("boards", help="List all boards with metrics")
    p.add_argument("--include-archived", action="store_true", help="Include archived boards")
    p.add_argument("--include-columns", action="store_true", help="Include column details")

    # board
    p = sub.add_parser("board", help="Get a specific board's details")
    p.add_argument("--include-columns", action="store_true", help="Include column details")

    # cards
    p = sub.add_parser("cards", help="List cards on a board")
    p.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p.add_argument("--count", type=int, default=100, help="Cards per page (default: 100, max: 100)")
    p.add_argument("--days-since-update", type=int, help="Filter by days since last update")
    p.add_argument("--include-archived", action="store_true", help="Include archived cards")
    add_filter_args(p)

    # card
    p = sub.add_parser("card", help="Get a single card by number")
    p.add_argument("--number", required=True, help="Card number")

    # create-card
    p = sub.add_parser("create-card", help="Create a single card")
    p.add_argument("--title", required=True, help="Card title")
    p.add_argument("--column-id", help="Target column ID")
    p.add_argument("--description", help="Card description (text or HTML)")
    p.add_argument("--description-file", help="Read description from file (overrides --description)")
    p.add_argument("--owner", help="Owner email address")
    p.add_argument("--priority", choices=["1", "2", "3", "4"], help="Priority level")
    p.add_argument("--label", help="Label name")
    p.add_argument("--size", choices=["S", "M", "L", "XL"], help="Card size")
    p.add_argument("--due", help="Due date (MM/DD/YYYY or ISO 8601)")
    p.add_argument("--template-id", help="Card template public ID (8-char)")
    p.add_argument("--add-to-top", action="store_true", help="Add to top of column")
    p.add_argument("--watcher", action="append", help="Watcher email (repeatable)")
    p.add_argument("--custom-field", action="append",
                   help="Custom field as 'Label=Value' (repeatable)")

    # create-cards
    p = sub.add_parser("create-cards", help="Create multiple cards from a JSON file")
    p.add_argument("--file", required=True, help="Path to JSON file with cards data")

    # update-card
    p = sub.add_parser("update-card", help="Update a card's fields")
    p.add_argument("--id", required=True, type=int, help="Card number")
    p.add_argument("--title", help="New title")
    p.add_argument("--description", help="New description")
    p.add_argument("--description-file", help="Read description from file (overrides --description)")
    p.add_argument("--column-id", help="Move to column ID")
    p.add_argument("--owner", help="Owner email")
    p.add_argument("--priority", choices=["1", "2", "3", "4"], help="Priority")
    p.add_argument("--label", help="Label name")
    p.add_argument("--size", choices=["S", "M", "L", "XL"], help="Card size")
    p.add_argument("--due", help="Due date")
    p.add_argument("--blocked", help="true or false")
    p.add_argument("--blocked-by", help="Blocker email")
    p.add_argument("--blocked-reason", help="Block reason")
    p.add_argument("--mirror-board", help="Board ID for mirrored cards")
    p.add_argument("--watcher", action="append", help="Watcher email (repeatable)")
    p.add_argument("--custom-field", action="append",
                   help="Custom field as 'Label=Value' (repeatable)")

    # move-card
    p = sub.add_parser("move-card", help="Move a card to a different column")
    p.add_argument("--id", required=True, type=int, help="Card number")
    p.add_argument("--column-id", required=True, help="Target column ID")
    p.add_argument("--mirror-board", help="Board ID for mirrored cards")

    # link-card
    p = sub.add_parser("link-card", help="Add a link to a card")
    p.add_argument("--id", required=True, type=int, help="Card number")
    link_target = p.add_mutually_exclusive_group(required=True)
    link_target.add_argument("--card", type=int, help="Target card number to link")
    link_target.add_argument("--url", help="External URL to link")
    p.add_argument("--type", help="Link type (default: 'related' for cards, 'external' for URLs)")
    p.add_argument("--title", help="Link title (for URL links)")
    p.add_argument("--mirror-board", help="Board ID for mirrored cards")

    # unlink-card
    p = sub.add_parser("unlink-card", help="Remove a link from a card")
    p.add_argument("--id", required=True, type=int, help="Card number")
    unlink_target = p.add_mutually_exclusive_group(required=True)
    unlink_target.add_argument("--card", type=int, help="Target card number to unlink")
    unlink_target.add_argument("--url", help="External URL to unlink")
    p.add_argument("--mirror-board", help="Board ID for mirrored cards")

    # search-cards
    p = sub.add_parser("search-cards", help="Search cards across all boards")
    p.add_argument("--query", help="Search title and description (case-insensitive)")
    p.add_argument("--label", help="Filter by label name (case-insensitive)")
    p.add_argument("--owner", help="Filter by owner email (case-insensitive)")
    p.add_argument("--priority", help="Filter by priority level")
    p.add_argument("--blocked", action="store_true", help="Show only blocked cards")
    p.add_argument("--include-archived", action="store_true", help="Include archived cards")

    # wip-check
    p = sub.add_parser("wip-check", help="Check WIP limits across board columns")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "boards": cmd_boards,
        "board": cmd_board,
        "cards": cmd_cards,
        "card": cmd_card,
        "create-card": cmd_create_card,
        "create-cards": cmd_create_cards,
        "update-card": cmd_update_card,
        "move-card": cmd_move_card,
        "link-card": cmd_link_card,
        "unlink-card": cmd_unlink_card,
        "search-cards": cmd_search_cards,
        "wip-check": cmd_wip_check,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
