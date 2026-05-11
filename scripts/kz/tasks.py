"""Tasks group: create, update, delete, move."""
from kz import http as kz_http
from kz import output as kz_output


def cmd_create(args, ctx):
    body = {"checklist": args.checklist, "description": args.description}
    if args.position is not None:
        body["position"] = args.position
    if args.due_at:
        body["dueAt"] = args.due_at
    resp = kz_http.api_request("POST", "/tasks", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.completed is not None:
        body["completed"] = bool(args.completed)
    if args.description is not None:
        body["description"] = args.description
    if args.position is not None:
        body["position"] = args.position
    if args.due_at is not None:
        body["dueAt"] = args.due_at
    if not body:
        raise ValueError("Provide one of --completed/--description/--position/--due-at")
    resp = kz_http.api_request("PATCH", f"/tasks/{args.id}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kz_http.api_request("DELETE", f"/tasks/{args.id}")
    kz_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_move(args, ctx):
    body = {
        "checklistFrom": args.checklist_from,
        "checklistTo": args.checklist_to,
        "position": args.position,
    }
    resp = kz_http.api_request("POST", f"/tasks/{args.id}/move", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("tasks", help="Tasks within a checklist.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("create", help="Add a task to a checklist.")
    p.add_argument("--checklist", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--position", type=int)
    p.add_argument("--due-at")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a task by ObjectId.")
    p.add_argument("--id", required=True)
    p.add_argument("--completed", type=lambda s: s.lower() == "true", default=None)
    p.add_argument("--description")
    p.add_argument("--position", type=int)
    p.add_argument("--due-at")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a task by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("move", help="Move a task between checklists or positions.")
    p.add_argument("--id", required=True)
    p.add_argument("--checklist-from", required=True)
    p.add_argument("--checklist-to", required=True)
    p.add_argument("--position", type=int, required=True)
    p.set_defaults(func=cmd_move)
