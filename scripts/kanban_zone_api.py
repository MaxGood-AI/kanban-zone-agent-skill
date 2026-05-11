#!/usr/bin/env python3
"""Kanban Zone CLI — v3 entry point.

Resource handlers live in scripts/kz/<resource>.py. Each resource module
exposes register(subparsers, ctx) that wires its grouped subparser into
the shared dispatcher.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kz import http as kz_http  # noqa: E402
from kz import output as kz_output  # noqa: E402
from kz.cache import Cache  # noqa: E402


def _load_env_file():
    candidates = [os.getcwd(), os.path.dirname(HERE)]
    for d in candidates:
        path = os.path.join(d, ".env")
        if os.path.isfile(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)


def _cache_path():
    override = os.environ.get("KANBANZONE_CACHE_PATH")
    if override:
        return override
    return os.path.expanduser("~/.kanbanzone-cache.json")


class Context:
    def __init__(self, args):
        self.board = args.board or os.environ.get("KANBAN_ZONE_BOARD_ID")
        self.pretty = args.pretty
        self.cache = Cache(_cache_path(), enabled=not args.no_cache)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="kanban_zone_api.py",
        description="Kanban Zone CLI (v3, wraps API v1.4).",
    )
    parser.add_argument("--board", help="Override KANBAN_ZONE_BOARD_ID for this call.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass the local cache; do not read or write it.")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON output.")
    parser.add_argument("--api-token", help="Override KANBAN_ZONE_API_KEY for this call.")

    sub = parser.add_subparsers(dest="group")
    sub.required = True

    from kz import org  # noqa: E402
    org.register(sub)

    from kz import boards  # noqa: E402
    boards.register(sub)

    from kz import cards  # noqa: E402
    cards.register(sub)

    from kz import comments  # noqa: E402
    comments.register(sub)

    from kz import checklists  # noqa: E402
    checklists.register(sub)

    from kz import tasks  # noqa: E402
    tasks.register(sub)

    from kz import tokens  # noqa: E402
    tokens.register(sub)

    from kz import webhooks  # noqa: E402
    webhooks.register(sub)

    return parser


def main(argv=None):
    _load_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.api_token:
        kz_http.set_api_token(args.api_token)
    ctx = Context(args)
    try:
        return args.func(args, ctx)
    except kz_http.KZApiError as exc:
        kz_output.error_exit(str(exc), status=exc.status)
    except (kz_http.KZAuthError, ValueError) as exc:
        kz_output.error_exit(str(exc))


if __name__ == "__main__":
    sys.exit(main() or 0)
