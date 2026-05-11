"""Comments group: add, list."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _resolve(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kz_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def _read_text(args):
    if args.text_file:
        with open(args.text_file) as f:
            return f.read()
    return args.text


def cmd_add(args, ctx):
    text = _read_text(args)
    if text is None:
        raise ValueError("Provide --text or --text-file")
    oid = _resolve(ctx, args.card)
    resp = kz_http.api_request("POST", "/comments", body={"card": oid, "text": text})
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve(ctx, args.card)
    resp = kz_http.api_request("GET", f"/cards/{oid}/comments")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("comments", help="Card comments.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("add", help="Add a comment to a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="List comments on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
