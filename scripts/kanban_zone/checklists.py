"""Checklists group: create, update, delete, list."""
from kanban_zone import http as kanban_zone_http
from kanban_zone import ids as kanban_zone_ids
from kanban_zone import output as kanban_zone_output


def _resolve_card(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kanban_zone_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def cmd_create(args, ctx):
    oid = _resolve_card(ctx, args.card)
    body = {"card": oid, "title": args.title}
    if args.task:
        body["tasks"] = [{"description": t} for t in args.task]
    resp = kanban_zone_http.api_request("POST", "/checklists", body=body)
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.title is not None:
        body["title"] = args.title
    if args.position is not None:
        body["position"] = args.position
    if not body:
        raise ValueError("Provide at least one of --title or --position")
    resp = kanban_zone_http.api_request("PATCH", f"/checklists/{args.id}", body=body)
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kanban_zone_http.delete_resource("checklist", f"/checklists/{args.id}")
    kanban_zone_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve_card(ctx, args.card)
    resp = kanban_zone_http.api_request("GET", f"/cards/{oid}/checklists")
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("checklists", help="Card checklists.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("create", help="Create a checklist on a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--task", action="append", default=[],
                   help="Inline task description (repeatable).")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a checklist by ObjectId.")
    p.add_argument("--id", required=True)
    p.add_argument("--title")
    p.add_argument("--position", type=int)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a checklist by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("list", help="List checklists on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
