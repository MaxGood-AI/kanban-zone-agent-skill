"""Tokens group: assign, revoke, list (card share tokens)."""
from kanban_zone import http as kanban_zone_http
from kanban_zone import ids as kanban_zone_ids
from kanban_zone import output as kanban_zone_output


def _resolve_card(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kanban_zone_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def cmd_assign(args, ctx):
    oid = _resolve_card(ctx, args.card)
    body = {"card": oid, "tokenId": args.token_id, "board": ctx.board}
    resp = kanban_zone_http.api_request("POST", "/tokens", body=body)
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)


def cmd_revoke(args, ctx):
    kanban_zone_http.delete_resource("token", f"/tokens/{args.id}")
    kanban_zone_output.print_json({"revoked": True, "id": args.id}, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve_card(ctx, args.card)
    resp = kanban_zone_http.api_request("GET", f"/cards/{oid}/tokens")
    kanban_zone_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("tokens", help="Card share tokens.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("assign", help="Assign a token to a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--token-id", required=True)
    p.set_defaults(func=cmd_assign)

    p = sub.add_parser("revoke", help="Revoke a card token by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_revoke)

    p = sub.add_parser("list", help="List tokens on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
