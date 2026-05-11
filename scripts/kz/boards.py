"""Boards group: list, get, columns, labels, members, custom-fields, templates."""
from kz import http as kz_http
from kz import output as kz_output


def _require_board(ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return ctx.board


def cmd_list(args, ctx):
    resp = kz_http.api_request("GET", "/boards", params={
        "includeArchived": args.include_archived,
        "includeColumns": args.include_columns,
    })
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}", params={
        "includeColumns": args.include_columns,
        "includeMembers": args.include_members,
        "includeLabels": args.include_labels,
        "includeCustomFields": args.include_custom_fields,
    })
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_columns(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/columns")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_labels(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/labels")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_members(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/members")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_custom_fields(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/custom-fields")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_templates(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/templates/{board}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("boards", help="Board listing and sub-resources.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("list", help="List all boards.")
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--include-columns", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get a board by --board.")
    p.add_argument("--include-columns", action="store_true")
    p.add_argument("--include-members", action="store_true")
    p.add_argument("--include-labels", action="store_true")
    p.add_argument("--include-custom-fields", action="store_true")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("columns", help="List columns for --board.")
    p.set_defaults(func=cmd_columns)

    p = sub.add_parser("labels", help="List labels for --board.")
    p.set_defaults(func=cmd_labels)

    p = sub.add_parser("members", help="List members for --board.")
    p.set_defaults(func=cmd_members)

    p = sub.add_parser("custom-fields", help="List custom fields for --board.")
    p.set_defaults(func=cmd_custom_fields)

    p = sub.add_parser("templates", help="List card templates for --board.")
    p.set_defaults(func=cmd_templates)
