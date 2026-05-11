"""Organization context — /me, /organization."""
from kz import http as kz_http
from kz import output as kz_output


def cmd_me(args, ctx):
    resp = kz_http.api_request("GET", "/me")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_context(args, ctx):
    params = {
        "includeBoards": args.include_boards,
        "includeMembers": args.include_members,
        "includeColumns": args.include_columns,
        "includeLabels": args.include_labels,
        "includeCustomFields": args.include_custom_fields,
    }
    resp = kz_http.api_request("GET", "/organization", params=params)
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("org", help="Organization context (me, context).")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    me = sub.add_parser("me", help="Verify the API key works.")
    me.set_defaults(func=cmd_me)

    ctx = sub.add_parser("context", help="Get organization context with optional includes.")
    ctx.add_argument("--include-boards", action="store_true")
    ctx.add_argument("--include-members", action="store_true")
    ctx.add_argument("--include-columns", action="store_true")
    ctx.add_argument("--include-labels", action="store_true")
    ctx.add_argument("--include-custom-fields", action="store_true")
    ctx.set_defaults(func=cmd_context)
