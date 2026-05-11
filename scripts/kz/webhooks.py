"""Webhooks group: list, get, create, update, delete, test, verify-signature."""
import hashlib
import hmac
import os

from kz import http as kz_http
from kz import output as kz_output


def cmd_list(args, ctx):
    resp = kz_http.api_request("GET", "/webhooks")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    resp = kz_http.api_request("GET", f"/webhooks/{args.id}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_create(args, ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    body = {"board": ctx.board, "event": args.event, "url": args.url}
    resp = kz_http.api_request("POST", "/webhooks", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.url is not None:
        body["url"] = args.url
    if args.event is not None:
        body["event"] = args.event
    if not body:
        raise ValueError("Provide --url or --event")
    resp = kz_http.api_request("PUT", f"/webhooks/{args.id}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kz_http.api_request("DELETE", f"/webhooks/{args.id}")
    kz_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_test(args, ctx):
    resp = kz_http.api_request("POST", f"/webhooks/{args.id}/test")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_verify_signature(args, ctx):
    key = args.webhook_key or os.environ.get("KZ_WEBHOOK_KEY")
    if not key:
        raise ValueError("Provide --webhook-key or set KZ_WEBHOOK_KEY")
    with open(args.payload_file, "rb") as f:
        payload = f.read()
    computed = hmac.new(key.encode("utf-8"), payload, hashlib.sha1).hexdigest()
    matched = hmac.compare_digest(computed, args.signature)
    kz_output.print_json({"verified": matched, "computed": computed},
                          pretty=ctx.pretty)
    return 0 if matched else 1


_EVENTS = ("CARD_CREATED", "CARD_MOVED", "CARD_UPDATED")


def register(subparsers):
    g = subparsers.add_parser("webhooks", help="Webhook CRUD + test + verify-signature.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    sub.add_parser("list", help="List webhooks for the active board.").set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get one webhook by id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("create", help="Register a webhook on the active board.")
    p.add_argument("--event", required=True, choices=_EVENTS)
    p.add_argument("--url", required=True)
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a webhook by id.")
    p.add_argument("--id", required=True)
    p.add_argument("--url")
    p.add_argument("--event", choices=_EVENTS)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a webhook by id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("test", help="Send a synthetic test event.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("verify-signature",
                       help="Verify an HMAC-SHA1 webhook signature locally.")
    p.add_argument("--webhook-key", help="Override KZ_WEBHOOK_KEY.")
    p.add_argument("--payload-file", required=True,
                   help="Bytes that were signed (notification.payload).")
    p.add_argument("--signature", required=True, help="X-KanbanZone-Signature value.")
    p.set_defaults(func=cmd_verify_signature)
