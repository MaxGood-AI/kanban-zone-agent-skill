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


def _parse_custom_fields(raw_list):
    out = []
    for raw in raw_list or []:
        if "=" not in raw:
            raise ValueError(f"--custom-field must be Key=Value, got {raw!r}")
        k, v = raw.split("=", 1)
        out.append({"label": k.strip(), "value": v.strip()})
    return out


def _read_description(args):
    if getattr(args, "description_file", None):
        with open(args.description_file) as f:
            return f.read()
    return getattr(args, "description", None)


def _card_input(args, include_title=True):
    body = {}
    if include_title and getattr(args, "title", None):
        body["title"] = args.title
    desc = _read_description(args)
    if desc is not None:
        body["description"] = desc
    for src, dst in [("column_id", "columnId"), ("owner", "owner"),
                     ("priority", "priority"), ("label", "label"),
                     ("size", "size"), ("due_at", "dueAt"),
                     ("blocked_reason", "blockedReason"),
                     ("template_id", "templateId")]:
        v = getattr(args, src, None)
        if v is not None:
            body[dst] = v
    blocked = getattr(args, "blocked", None)
    if blocked is True:
        body["blocked"] = True
    elif blocked is False and "blocked" in vars(args):
        # explicit false from update - only include if user passed --blocked false
        pass
    if getattr(args, "watcher", None):
        body["watchers"] = list(args.watcher)
    cf = _parse_custom_fields(getattr(args, "custom_field", None))
    if cf:
        body["customFields"] = cf
    return body


def cmd_create(args, ctx):
    board = _require_board(ctx)
    body = {"board": board, "addToTop": bool(getattr(args, "add_to_top", False)),
            "cards": [_card_input(args, include_title=True)]}
    resp = kz_http.api_request("POST", "/cards", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_create_bulk(args, ctx):
    with open(args.file) as f:
        payload = __import__("json").load(f)
    if "board" not in payload:
        payload["board"] = _require_board(ctx)
    resp = kz_http.api_request("POST", "/cards", body=payload)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = _card_input(args, include_title=True)
    body["board"] = board
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_move(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "columnId": args.column_id,
            "addToTop": bool(getattr(args, "add_to_top", False))}
    resp = kz_http.api_request("POST", f"/cards/{oid}/move", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    kz_http.api_request("DELETE", f"/cards/{oid}", params={"board": board})
    ctx.cache.invalidate_card(board, oid)
    kz_output.print_json({"deleted": True, "id": oid}, pretty=ctx.pretty)


def _links_payload(action, args):
    if args.card is not None:
        item = {"card": int(args.card)}
        if action == "add":
            item["type"] = args.type or "related"
        return {action: [item]}
    if args.url:
        item = {"url": args.url}
        if action == "add":
            item["title"] = args.title or args.url
            item["type"] = args.type or "external"
        return {action: [item]}
    raise ValueError("Provide either --card or --url")


def cmd_links_add(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "links": _links_payload("add", args)}
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_links_remove(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "links": _links_payload("remove", args)}
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def _fetch_all_cards(board, include_archived=False):
    page = 1
    out = []
    while True:
        resp = kz_http.api_request("GET", "/cards", params={
            "board": board, "page": page, "count": 100,
            "includeArchived": include_archived,
        }) or {}
        out.extend(resp.get("cards", []))
        if not resp.get("hasMore"):
            break
        page += 1
    return out


def cmd_search(args, ctx):
    boards_resp = kz_http.api_request("GET", "/boards",
                                       params={"includeArchived": False}) or {}
    matches = []
    for b in boards_resp.get("boards", []):
        cards = _fetch_all_cards(b["publicId"])
        filtered = _filter_cards(
            cards, label=args.label, owner=args.owner, query=args.query,
        )
        for c in filtered:
            c2 = dict(c)
            c2["_board"] = b["publicId"]
            c2["_boardName"] = b.get("name")
            matches.append(c2)
    kz_output.print_json({"count": len(matches), "cards": matches},
                          pretty=ctx.pretty)


def cmd_wip_check(args, ctx):
    board = _require_board(ctx)
    board_resp = kz_http.api_request("GET", f"/boards/{board}", params={
        "includeColumns": True, "includeMembers": False,
        "includeLabels": False, "includeCustomFields": False,
    }) or {}
    cards = _fetch_all_cards(board)
    counts = {}
    for c in cards:
        cid = c.get("columnId") or c.get("column")
        counts[cid] = counts.get(cid, 0) + 1
    report = []
    for col in board_resp.get("columns", []):
        cid = col.get("_id") or col.get("columnId")
        n = counts.get(cid, 0)
        min_w = col.get("minWIP") or 0
        max_w = col.get("maxWIP") or 0
        status = "ok"
        if max_w and n > max_w:
            status = "violation"
        elif min_w and n < min_w:
            status = "below_min"
        report.append({
            "columnId": cid, "title": col.get("title"),
            "current": n, "minWIP": min_w, "maxWIP": max_w, "status": status,
        })
    kz_output.print_json({"board": board, "columns": report},
                          pretty=ctx.pretty)


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

    p = sub.add_parser("create", help="Create a card.")
    p.add_argument("--title", required=True)
    p.add_argument("--description")
    p.add_argument("--description-file")
    p.add_argument("--column-id")
    p.add_argument("--owner")
    p.add_argument("--priority")
    p.add_argument("--label")
    p.add_argument("--size")
    p.add_argument("--due-at")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--blocked-reason")
    p.add_argument("--add-to-top", action="store_true")
    p.add_argument("--watcher", action="append", default=[])
    p.add_argument("--custom-field", action="append", default=[])
    p.add_argument("--template-id")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("create-bulk", help="Create many cards from a JSON file.")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_create_bulk)

    p = sub.add_parser("update", help="Update a card by --id (number or OID).")
    p.add_argument("--id", required=True)
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--description-file")
    p.add_argument("--owner")
    p.add_argument("--priority")
    p.add_argument("--label")
    p.add_argument("--size")
    p.add_argument("--due-at")
    p.add_argument("--blocked", type=lambda s: s.lower() == "true", default=None)
    p.add_argument("--blocked-reason")
    p.add_argument("--watcher", action="append", default=[])
    p.add_argument("--custom-field", action="append", default=[])
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("move", help="Move a card to a column.")
    p.add_argument("--id", required=True)
    p.add_argument("--column-id", required=True)
    p.add_argument("--add-to-top", action="store_true")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("delete", help="Delete a card by --id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("links-add", help="Add a card-to-card or URL link.")
    p.add_argument("--id", required=True)
    p.add_argument("--card", type=int)
    p.add_argument("--url")
    p.add_argument("--title")
    p.add_argument("--type", default=None)
    p.set_defaults(func=cmd_links_add)

    p = sub.add_parser("links-remove", help="Remove a card-to-card or URL link.")
    p.add_argument("--id", required=True)
    p.add_argument("--card", type=int)
    p.add_argument("--url")
    p.set_defaults(func=cmd_links_remove)

    p = sub.add_parser("search", help="Cross-board card search.")
    p.add_argument("--query")
    p.add_argument("--label")
    p.add_argument("--owner")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("wip-check", help="Compare counts to per-column WIP limits.")
    p.set_defaults(func=cmd_wip_check)
