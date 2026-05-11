"""Hidden v2 flat-command aliases. Suppressed from --help, kept for back-compat.

Each alias mirrors the v2 CLI surface and dispatches to the equivalent v3
grouped handler so existing scripts keep working without code changes.
"""
import argparse

from kz import boards as kz_boards
from kz import cards as kz_cards

# Names registered by this module — used to rebuild the metavar after each
# _add() call so suppressed aliases stay out of the usage line.
_HIDDEN_NAMES: set = set()


def _add(sub, name, callback, configure=lambda p: None):
    p = sub.add_parser(name, help=argparse.SUPPRESS)
    configure(p)
    p.set_defaults(func=callback)
    # Python ≥ 3.14 changed argparse so that help=SUPPRESS on a subparser
    # still renders as "==SUPPRESS==" in --help output and still includes the
    # name in the metavar.  Work around both by:
    #   1. Removing the entry from _choices_actions (hides from the listing).
    #   2. Rebuilding the metavar from only the non-suppressed choices.
    _HIDDEN_NAMES.add(name)
    if hasattr(sub, "_choices_actions"):
        sub._choices_actions = [
            a for a in sub._choices_actions if a.dest != name
        ]
        visible = [k for k in sub.choices if k not in _HIDDEN_NAMES]
        sub.metavar = "{" + ",".join(visible) + "}"
    return p


def _wrap_boards_list(args, ctx):
    args.include_archived = getattr(args, "include_archived", False)
    args.include_columns = getattr(args, "include_columns", False)
    return kz_boards.cmd_list(args, ctx)


def _wrap_boards_get(args, ctx):
    args.include_columns = getattr(args, "include_columns", False)
    args.include_members = False
    args.include_labels = False
    args.include_custom_fields = False
    return kz_boards.cmd_get(args, ctx)


def _wrap_cards_list(args, ctx):
    args.page = getattr(args, "page", 1)
    args.count = getattr(args, "count", 100)
    args.include_archived = getattr(args, "include_archived", False)
    args.days_since_last_update = getattr(args, "days_since_last_update", None)
    for k in ("label", "owner", "column", "priority", "query"):
        setattr(args, k, getattr(args, k, None))
    args.blocked = getattr(args, "blocked", False)
    return kz_cards.cmd_list(args, ctx)


def _wrap_cards_get(args, ctx):
    args.id = args.number  # v2 used --number
    return kz_cards.cmd_get(args, ctx)


def _wrap_cards_create(args, ctx):
    return kz_cards.cmd_create(args, ctx)


def _wrap_cards_create_bulk(args, ctx):
    return kz_cards.cmd_create_bulk(args, ctx)


def _wrap_cards_update(args, ctx):
    args.id = str(args.id)  # accepts number-as-int from v2
    return kz_cards.cmd_update(args, ctx)


def _wrap_cards_move(args, ctx):
    args.id = str(args.id)
    args.add_to_top = getattr(args, "add_to_top", False)
    return kz_cards.cmd_move(args, ctx)


def _wrap_cards_links_add(args, ctx):
    args.id = str(args.id)
    return kz_cards.cmd_links_add(args, ctx)


def _wrap_cards_links_remove(args, ctx):
    args.id = str(args.id)
    return kz_cards.cmd_links_remove(args, ctx)


def _wrap_cards_search(args, ctx):
    return kz_cards.cmd_search(args, ctx)


def _wrap_cards_wip_check(args, ctx):
    return kz_cards.cmd_wip_check(args, ctx)


def register(subparsers):
    # "boards" and "cards" are already registered as group parsers; the group
    # parsers already respond correctly to `boards --help` / `cards --help`
    # (exit 0, show subcommand list).  Re-registering those names would raise
    # ValueError: conflicting subparser on Python ≥ 3.14, so we skip them.
    # All other legacy flat names are safe to register because the groups use
    # different names (boards, cards, comments, …) while the flat aliases are
    # singular or hyphenated (board, card, create-card, …).

    # board  (alias for `boards get`)
    _add(subparsers, "board", _wrap_boards_get, lambda p: (
        p.add_argument("--include-columns", action="store_true"),
    ))

    # card  (alias for `cards get`, uses legacy --number flag)
    _add(subparsers, "card", _wrap_cards_get, lambda p: (
        p.add_argument("--number", required=True),
    ))

    # create-card / create-cards
    _add(subparsers, "create-card", _wrap_cards_create, lambda p: (
        p.add_argument("--title", required=True),
        p.add_argument("--description"),
        p.add_argument("--description-file"),
        p.add_argument("--column-id"),
        p.add_argument("--owner"),
        p.add_argument("--priority"),
        p.add_argument("--label"),
        p.add_argument("--size"),
        p.add_argument("--due-at"),
        p.add_argument("--blocked", action="store_true"),
        p.add_argument("--blocked-reason"),
        p.add_argument("--add-to-top", action="store_true"),
        p.add_argument("--watcher", action="append", default=[]),
        p.add_argument("--custom-field", action="append", default=[]),
        p.add_argument("--template-id"),
    ))
    _add(subparsers, "create-cards", _wrap_cards_create_bulk, lambda p: (
        p.add_argument("--file", required=True),
    ))

    # update-card / move-card
    _add(subparsers, "update-card", _wrap_cards_update, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--title"),
        p.add_argument("--description"),
        p.add_argument("--description-file"),
        p.add_argument("--owner"),
        p.add_argument("--priority"),
        p.add_argument("--label"),
        p.add_argument("--size"),
        p.add_argument("--due-at"),
        p.add_argument("--blocked", type=lambda s: s.lower() == "true", default=None),
        p.add_argument("--blocked-reason"),
        p.add_argument("--watcher", action="append", default=[]),
        p.add_argument("--custom-field", action="append", default=[]),
    ))
    _add(subparsers, "move-card", _wrap_cards_move, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--column-id", required=True),
        p.add_argument("--add-to-top", action="store_true"),
    ))

    # link-card / unlink-card
    _add(subparsers, "link-card", _wrap_cards_links_add, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--card", type=int),
        p.add_argument("--url"),
        p.add_argument("--title"),
        p.add_argument("--type", default=None),
    ))
    _add(subparsers, "unlink-card", _wrap_cards_links_remove, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--card", type=int),
        p.add_argument("--url"),
    ))

    # search-cards / wip-check
    _add(subparsers, "search-cards", _wrap_cards_search, lambda p: (
        p.add_argument("--query"),
        p.add_argument("--label"),
        p.add_argument("--owner"),
    ))
    _add(subparsers, "wip-check", _wrap_cards_wip_check, lambda p: None)
