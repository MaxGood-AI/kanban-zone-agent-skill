"""Cards group. Split across three logical sections: read, write, cross-cutting.

This file holds all card subcommands; they are grouped here for cohesion since
they share helpers (board resolution, OID resolution, client-side filters)."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _require_board(ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return ctx.board


def _resolve(ctx, value):
    return kz_ids.resolve_card_object_id(value, _require_board(ctx), ctx.cache)


def _get_field(card, name):
    if name in card:
        return card[name]
    return (card.get("custom") or {}).get(name)


def _filter_cards(cards, label=None, owner=None, column=None, priority=None,
                  blocked=False, query=None):
    out = []
    for c in cards:
        if label and _get_field(c, "label") != label:
            continue
        if owner and _get_field(c, "owner") != owner:
            continue
        if column:
            colname = c.get("columnTitle") or c.get("column")
            if colname != column:
                continue
        if priority is not None and str(_get_field(c, "priority")) != str(priority):
            continue
        if blocked and not c.get("blocked"):
            continue
        if query:
            haystack = " ".join(str(c.get(k, "")) for k in ("title", "description"))
            if query.lower() not in haystack.lower():
                continue
        out.append(c)
    return out


def cmd_list(args, ctx):
    board = _require_board(ctx)
    params = {
        "board": board, "page": args.page, "count": args.count,
        "includeArchived": args.include_archived,
    }
    if args.days_since_last_update is not None:
        params["daysSinceLastUpdate"] = args.days_since_last_update
    resp = kz_http.api_request("GET", "/cards", params=params)
    if any([args.label, args.owner, args.column, args.priority, args.blocked, args.query]):
        resp = dict(resp or {})
        cards = _filter_cards(
            resp.get("cards", []),
            label=args.label, owner=args.owner, column=args.column,
            priority=args.priority, blocked=args.blocked, query=args.query,
        )
        resp["cards"] = cards
        resp["count"] = len(cards)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    oid = _resolve(ctx, args.id)
    resp = kz_http.api_request("GET", f"/cards/{oid}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_history(args, ctx):
    oid = _resolve(ctx, args.id)
    params = {}
    if args.from_date:
        params["from"] = args.from_date
    resp = kz_http.api_request("GET", f"/cards/{oid}/history", params=params or None)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_metrics(args, ctx):
    oid = _resolve(ctx, args.id)
    resp = kz_http.api_request("GET", f"/cards/{oid}/metrics")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("cards", help="Card CRUD, history, metrics, links, search.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("list", help="List cards on the active board.")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--days-since-last-update", type=int, default=None)
    p.add_argument("--label")
    p.add_argument("--owner")
    p.add_argument("--column")
    p.add_argument("--priority")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--query")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get one card by number or ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("history", help="Card history.")
    p.add_argument("--id", required=True)
    p.add_argument("--from-date", help="ISO date.")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("metrics", help="Card metrics.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_metrics)
