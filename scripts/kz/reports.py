"""Reports group: 8 report types, all GET /boards/{publicId}/reports/{type}."""
from kz import http as kz_http
from kz import output as kz_output


def _run_report(report_type, args, ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    params = {}
    if args.from_date:
        params["from"] = args.from_date
    if args.to_date:
        params["to"] = args.to_date
    resp = kz_http.api_request(
        "GET", f"/boards/{ctx.board}/reports/{report_type}",
        params=params or None,
    )
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_throughput(args, ctx): _run_report("throughput", args, ctx)
def cmd_arrival_rate(args, ctx): _run_report("arrival-rate", args, ctx)
def cmd_cycle_time(args, ctx): _run_report("cycle-time", args, ctx)
def cmd_lead_time(args, ctx): _run_report("lead-time", args, ctx)
def cmd_flow(args, ctx): _run_report("flow", args, ctx)
def cmd_flow_efficiency(args, ctx): _run_report("flow-efficiency", args, ctx)
def cmd_allocation(args, ctx): _run_report("allocation", args, ctx)
def cmd_abandoned_effort(args, ctx): _run_report("abandoned-effort", args, ctx)


_REPORTS = [
    ("throughput", cmd_throughput),
    ("arrival-rate", cmd_arrival_rate),
    ("cycle-time", cmd_cycle_time),
    ("lead-time", cmd_lead_time),
    ("flow", cmd_flow),
    ("flow-efficiency", cmd_flow_efficiency),
    ("allocation", cmd_allocation),
    ("abandoned-effort", cmd_abandoned_effort),
]


def register(subparsers):
    g = subparsers.add_parser("reports", help="Board-level analytics reports.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True
    for slug, handler in _REPORTS:
        p = sub.add_parser(slug, help=f"{slug} report")
        p.add_argument("--from-date", "--from",
                       help="ISO date (e.g. 2026-01-01). --from is an alias.")
        p.add_argument("--to-date", "--to",
                       help="ISO date (e.g. 2026-04-01). --to is an alias.")
        p.set_defaults(func=handler)
