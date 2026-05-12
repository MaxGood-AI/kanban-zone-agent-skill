"""Test that every register() function is callable and wires up subparsers.

These tests exercise the argparse registration code paths that the handler-level
tests don't touch. They call register() on a real subparsers object and parse
known-good command lines through the resulting parser.
"""
import argparse
import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")

from kz import boards as kz_boards
from kz import cards as kz_cards
from kz import checklists as kz_chk
from kz import comments as kz_comments
from kz import legacy as kz_legacy
from kz import org as kz_org
from kz import reports as kz_reports
from kz import tasks as kz_tasks
from kz import tokens as kz_tokens
from kz import webhooks as kz_webhooks
from tests.fakes import FakeApi


def _make_parser(*register_fns):
    """Build a minimal top-level parser and call each register_fn on its subparsers."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="group")
    for fn in register_fns:
        fn(sub)
    return parser, sub


class TestOrgRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_org.register)

    def test_org_me_is_parseable(self):
        args = self.parser.parse_args(["org", "me"])
        self.assertEqual(args.func, kz_org.cmd_me)

    def test_org_context_defaults(self):
        args = self.parser.parse_args(["org", "context"])
        self.assertFalse(args.include_boards)
        self.assertFalse(args.include_members)
        self.assertFalse(args.include_columns)
        self.assertFalse(args.include_labels)
        self.assertFalse(args.include_custom_fields)

    def test_org_context_all_flags(self):
        args = self.parser.parse_args([
            "org", "context",
            "--include-boards", "--include-members",
            "--include-columns", "--include-labels",
            "--include-custom-fields",
        ])
        self.assertTrue(args.include_boards)
        self.assertTrue(args.include_members)
        self.assertTrue(args.include_columns)
        self.assertTrue(args.include_labels)
        self.assertTrue(args.include_custom_fields)


class TestBoardsRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_boards.register)

    def test_boards_list_is_parseable(self):
        args = self.parser.parse_args(["boards", "list"])
        self.assertEqual(args.func, kz_boards.cmd_list)
        self.assertFalse(args.include_archived)
        self.assertFalse(args.include_columns)

    def test_boards_list_with_flags(self):
        args = self.parser.parse_args(["boards", "list", "--include-archived", "--include-columns"])
        self.assertTrue(args.include_archived)
        self.assertTrue(args.include_columns)

    def test_boards_get_is_parseable(self):
        args = self.parser.parse_args(["boards", "get"])
        self.assertEqual(args.func, kz_boards.cmd_get)
        self.assertFalse(args.include_columns)
        self.assertFalse(args.include_members)
        self.assertFalse(args.include_labels)
        self.assertFalse(args.include_custom_fields)

    def test_boards_get_all_flags(self):
        args = self.parser.parse_args([
            "boards", "get",
            "--include-columns", "--include-members",
            "--include-labels", "--include-custom-fields",
        ])
        self.assertTrue(args.include_columns)
        self.assertTrue(args.include_members)
        self.assertTrue(args.include_labels)
        self.assertTrue(args.include_custom_fields)

    def test_boards_columns_is_parseable(self):
        args = self.parser.parse_args(["boards", "columns"])
        self.assertEqual(args.func, kz_boards.cmd_columns)

    def test_boards_labels_is_parseable(self):
        args = self.parser.parse_args(["boards", "labels"])
        self.assertEqual(args.func, kz_boards.cmd_labels)

    def test_boards_members_is_parseable(self):
        args = self.parser.parse_args(["boards", "members"])
        self.assertEqual(args.func, kz_boards.cmd_members)

    def test_boards_custom_fields_is_parseable(self):
        args = self.parser.parse_args(["boards", "custom-fields"])
        self.assertEqual(args.func, kz_boards.cmd_custom_fields)

    def test_boards_templates_is_parseable(self):
        args = self.parser.parse_args(["boards", "templates"])
        self.assertEqual(args.func, kz_boards.cmd_templates)

    def test_boards_no_subcommand_defaults_to_list(self):
        args = self.parser.parse_args(["boards"])
        self.assertEqual(args.func, kz_boards.cmd_list)


class TestCardsRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_cards.register)

    def test_cards_list_is_parseable(self):
        args = self.parser.parse_args(["cards", "list"])
        self.assertEqual(args.func, kz_cards.cmd_list)
        self.assertEqual(args.page, 1)
        self.assertEqual(args.count, 100)

    def test_cards_list_all_filters(self):
        args = self.parser.parse_args([
            "cards", "list",
            "--page", "2", "--count", "50",
            "--label", "Bug", "--owner", "alice",
            "--column", "Doing", "--priority", "high",
            "--blocked", "--query", "deploy",
        ])
        self.assertEqual(args.page, 2)
        self.assertEqual(args.count, 50)
        self.assertEqual(args.label, "Bug")
        self.assertEqual(args.owner, "alice")
        self.assertEqual(args.column, "Doing")
        self.assertEqual(args.priority, "high")
        self.assertTrue(args.blocked)
        self.assertEqual(args.query, "deploy")

    def test_cards_get_is_parseable(self):
        args = self.parser.parse_args(["cards", "get", "--id", "42"])
        self.assertEqual(args.func, kz_cards.cmd_get)
        self.assertEqual(args.id, "42")

    def test_cards_history_is_parseable(self):
        args = self.parser.parse_args(["cards", "history", "--id", "42"])
        self.assertEqual(args.func, kz_cards.cmd_history)

    def test_cards_history_with_from_date(self):
        args = self.parser.parse_args([
            "cards", "history", "--id", "42", "--from-date", "2026-01-01",
        ])
        self.assertEqual(args.from_date, "2026-01-01")

    def test_cards_metrics_is_parseable(self):
        args = self.parser.parse_args(["cards", "metrics", "--id", "42"])
        self.assertEqual(args.func, kz_cards.cmd_metrics)

    def test_cards_create_is_parseable(self):
        args = self.parser.parse_args(["cards", "create", "--title", "New Card"])
        self.assertEqual(args.func, kz_cards.cmd_create)
        self.assertEqual(args.title, "New Card")

    def test_cards_create_all_fields(self):
        args = self.parser.parse_args([
            "cards", "create", "--title", "T",
            "--description", "D", "--column-id", "COL1",
            "--owner", "bob", "--priority", "high",
            "--label", "Bug", "--size", "3",
            "--due-at", "2026-12-31", "--blocked",
            "--blocked-reason", "waiting",
            "--add-to-top",
            "--watcher", "a@b.com", "--watcher", "c@d.com",
            "--custom-field", "Sprint=1",
            "--template-id", "TPL1",
        ])
        self.assertEqual(args.title, "T")
        self.assertEqual(args.watcher, ["a@b.com", "c@d.com"])
        self.assertTrue(args.blocked)

    def test_cards_create_bulk_is_parseable(self):
        args = self.parser.parse_args(["cards", "create-bulk", "--file", "x.json"])
        self.assertEqual(args.func, kz_cards.cmd_create_bulk)
        self.assertEqual(args.file, "x.json")

    def test_cards_update_is_parseable(self):
        args = self.parser.parse_args(["cards", "update", "--id", "42"])
        self.assertEqual(args.func, kz_cards.cmd_update)

    def test_cards_move_is_parseable(self):
        args = self.parser.parse_args(["cards", "move", "--id", "42", "--column-id", "C1"])
        self.assertEqual(args.func, kz_cards.cmd_move)

    def test_cards_delete_is_parseable(self):
        args = self.parser.parse_args(["cards", "delete", "--id", "42"])
        self.assertEqual(args.func, kz_cards.cmd_delete)

    def test_cards_links_add_is_parseable(self):
        args = self.parser.parse_args([
            "cards", "links-add", "--id", "42", "--card", "99",
        ])
        self.assertEqual(args.func, kz_cards.cmd_links_add)

    def test_cards_links_remove_is_parseable(self):
        args = self.parser.parse_args([
            "cards", "links-remove", "--id", "42", "--card", "99",
        ])
        self.assertEqual(args.func, kz_cards.cmd_links_remove)

    def test_cards_search_is_parseable(self):
        args = self.parser.parse_args(["cards", "search"])
        self.assertEqual(args.func, kz_cards.cmd_search)

    def test_cards_wip_check_is_parseable(self):
        args = self.parser.parse_args(["cards", "wip-check"])
        self.assertEqual(args.func, kz_cards.cmd_wip_check)

    def test_cards_no_subcommand_defaults_to_list(self):
        args = self.parser.parse_args(["cards"])
        self.assertEqual(args.func, kz_cards.cmd_list)


class TestCommentsRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_comments.register)

    def test_comments_add_is_parseable(self):
        args = self.parser.parse_args(["comments", "add", "--card", "42", "--text", "hi"])
        self.assertEqual(args.func, kz_comments.cmd_add)
        self.assertEqual(args.card, "42")
        self.assertEqual(args.text, "hi")

    def test_comments_add_with_text_file(self):
        args = self.parser.parse_args([
            "comments", "add", "--card", "42", "--text-file", "/tmp/t.txt",
        ])
        self.assertEqual(args.text_file, "/tmp/t.txt")

    def test_comments_list_is_parseable(self):
        args = self.parser.parse_args(["comments", "list", "--card", "42"])
        self.assertEqual(args.func, kz_comments.cmd_list)


class TestChecklistsRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_chk.register)

    def test_checklists_create_is_parseable(self):
        args = self.parser.parse_args([
            "checklists", "create", "--card", "42", "--title", "QA",
        ])
        self.assertEqual(args.func, kz_chk.cmd_create)
        self.assertEqual(args.title, "QA")
        self.assertEqual(args.task, [])

    def test_checklists_create_with_tasks(self):
        args = self.parser.parse_args([
            "checklists", "create", "--card", "42", "--title", "QA",
            "--task", "First", "--task", "Second",
        ])
        self.assertEqual(args.task, ["First", "Second"])

    def test_checklists_update_is_parseable(self):
        args = self.parser.parse_args([
            "checklists", "update", "--id", "abc123", "--title", "Renamed",
        ])
        self.assertEqual(args.func, kz_chk.cmd_update)
        self.assertEqual(args.id, "abc123")

    def test_checklists_update_with_position(self):
        args = self.parser.parse_args([
            "checklists", "update", "--id", "abc123", "--position", "2",
        ])
        self.assertEqual(args.position, 2)

    def test_checklists_delete_is_parseable(self):
        args = self.parser.parse_args(["checklists", "delete", "--id", "abc123"])
        self.assertEqual(args.func, kz_chk.cmd_delete)

    def test_checklists_list_is_parseable(self):
        args = self.parser.parse_args(["checklists", "list", "--card", "42"])
        self.assertEqual(args.func, kz_chk.cmd_list)


class TestTasksRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_tasks.register)

    def test_tasks_create_is_parseable(self):
        args = self.parser.parse_args([
            "tasks", "create", "--checklist", "CHK1", "--description", "Do X",
        ])
        self.assertEqual(args.func, kz_tasks.cmd_create)
        self.assertEqual(args.checklist, "CHK1")
        self.assertEqual(args.description, "Do X")
        self.assertIsNone(args.position)
        self.assertIsNone(args.due_at)

    def test_tasks_create_with_position_and_due(self):
        args = self.parser.parse_args([
            "tasks", "create", "--checklist", "CHK1", "--description", "X",
            "--position", "0", "--due-at", "2026-06-01",
        ])
        self.assertEqual(args.position, 0)
        self.assertEqual(args.due_at, "2026-06-01")

    def test_tasks_update_is_parseable(self):
        args = self.parser.parse_args(["tasks", "update", "--id", "TASK1"])
        self.assertEqual(args.func, kz_tasks.cmd_update)
        self.assertIsNone(args.completed)
        self.assertIsNone(args.description)
        self.assertIsNone(args.position)
        self.assertIsNone(args.due_at)

    def test_tasks_update_completed_true(self):
        args = self.parser.parse_args([
            "tasks", "update", "--id", "TASK1", "--completed", "true",
        ])
        self.assertTrue(args.completed)

    def test_tasks_update_completed_false(self):
        args = self.parser.parse_args([
            "tasks", "update", "--id", "TASK1", "--completed", "false",
        ])
        self.assertFalse(args.completed)

    def test_tasks_delete_is_parseable(self):
        args = self.parser.parse_args(["tasks", "delete", "--id", "TASK1"])
        self.assertEqual(args.func, kz_tasks.cmd_delete)

    def test_tasks_move_is_parseable(self):
        args = self.parser.parse_args([
            "tasks", "move", "--id", "TASK1",
            "--checklist-from", "CHK1", "--checklist-to", "CHK2",
            "--position", "3",
        ])
        self.assertEqual(args.func, kz_tasks.cmd_move)
        self.assertEqual(args.checklist_from, "CHK1")
        self.assertEqual(args.checklist_to, "CHK2")
        self.assertEqual(args.position, 3)


class TestTokensRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_tokens.register)

    def test_tokens_assign_is_parseable(self):
        args = self.parser.parse_args([
            "tokens", "assign", "--card", "42", "--token-id", "TKN1",
        ])
        self.assertEqual(args.func, kz_tokens.cmd_assign)
        self.assertEqual(args.card, "42")
        self.assertEqual(args.token_id, "TKN1")

    def test_tokens_revoke_is_parseable(self):
        args = self.parser.parse_args(["tokens", "revoke", "--id", "TOKID"])
        self.assertEqual(args.func, kz_tokens.cmd_revoke)
        self.assertEqual(args.id, "TOKID")

    def test_tokens_list_is_parseable(self):
        args = self.parser.parse_args(["tokens", "list", "--card", "42"])
        self.assertEqual(args.func, kz_tokens.cmd_list)


class TestWebhooksRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_webhooks.register)

    def test_webhooks_list_is_parseable(self):
        args = self.parser.parse_args(["webhooks", "list"])
        self.assertEqual(args.func, kz_webhooks.cmd_list)

    def test_webhooks_get_is_parseable(self):
        args = self.parser.parse_args(["webhooks", "get", "--id", "HK1"])
        self.assertEqual(args.func, kz_webhooks.cmd_get)

    def test_webhooks_create_is_parseable(self):
        args = self.parser.parse_args([
            "webhooks", "create",
            "--event", "CARD_CREATED", "--url", "https://h.example/wh",
        ])
        self.assertEqual(args.func, kz_webhooks.cmd_create)
        self.assertEqual(args.event, "CARD_CREATED")

    def test_webhooks_update_is_parseable(self):
        args = self.parser.parse_args([
            "webhooks", "update", "--id", "HK1", "--url", "https://h.example/v2",
        ])
        self.assertEqual(args.func, kz_webhooks.cmd_update)

    def test_webhooks_delete_is_parseable(self):
        args = self.parser.parse_args(["webhooks", "delete", "--id", "HK1"])
        self.assertEqual(args.func, kz_webhooks.cmd_delete)

    def test_webhooks_test_is_parseable(self):
        args = self.parser.parse_args(["webhooks", "test", "--id", "HK1"])
        self.assertEqual(args.func, kz_webhooks.cmd_test)

    def test_webhooks_verify_signature_is_parseable(self):
        args = self.parser.parse_args([
            "webhooks", "verify-signature",
            "--payload-file", "/tmp/p.json",
            "--signature", "aabbcc",
        ])
        self.assertEqual(args.func, kz_webhooks.cmd_verify_signature)
        self.assertIsNone(args.webhook_key)

    def test_webhooks_verify_signature_with_key(self):
        args = self.parser.parse_args([
            "webhooks", "verify-signature",
            "--webhook-key", "mykey",
            "--payload-file", "/tmp/p.json",
            "--signature", "aabbcc",
        ])
        self.assertEqual(args.webhook_key, "mykey")


class TestReportsRegister(unittest.TestCase):
    def setUp(self):
        self.parser, self.sub = _make_parser(kz_reports.register)

    def test_all_report_types_are_parseable(self):
        slugs = [
            "throughput", "arrival-rate", "cycle-time", "lead-time",
            "flow", "flow-efficiency", "allocation", "abandoned-effort",
        ]
        for slug in slugs:
            with self.subTest(slug=slug):
                args = self.parser.parse_args(["reports", slug])
                self.assertIsNone(args.from_date)
                self.assertIsNone(args.to_date)

    def test_report_with_dates(self):
        args = self.parser.parse_args([
            "reports", "throughput",
            "--from-date", "2026-01-01", "--to-date", "2026-04-01",
        ])
        self.assertEqual(args.from_date, "2026-01-01")
        self.assertEqual(args.to_date, "2026-04-01")


class TestLegacyRegister(unittest.TestCase):
    """Exercise legacy.register() and each _wrap_* function."""

    def setUp(self):
        # Legacy aliases share the same subparsers as the v3 groups, so we
        # register all groups then the legacy aliases on one parser.
        from kz import boards as _b, cards as _c
        self.parser = argparse.ArgumentParser()
        sub = self.parser.add_subparsers(dest="group")
        _b.register(sub)
        _c.register(sub)
        kz_legacy.register(sub)
        self.sub = sub

    def test_board_alias_parseable(self):
        args = self.parser.parse_args(["board"])
        # func is _wrap_boards_get
        self.assertIsNotNone(args.func)

    def test_board_with_include_columns(self):
        args = self.parser.parse_args(["board", "--include-columns"])
        self.assertTrue(args.include_columns)

    def test_card_alias_parseable(self):
        args = self.parser.parse_args(["card", "--number", "42"])
        self.assertEqual(args.number, "42")

    def test_create_card_alias_parseable(self):
        args = self.parser.parse_args(["create-card", "--title", "New"])
        self.assertEqual(args.title, "New")

    def test_create_card_all_fields(self):
        args = self.parser.parse_args([
            "create-card", "--title", "T",
            "--description", "D",
            "--column-id", "COL1",
            "--owner", "alice",
            "--priority", "high",
            "--label", "Bug",
            "--size", "2",
            "--due-at", "2026-12-31",
            "--blocked",
            "--blocked-reason", "dep",
            "--add-to-top",
            "--watcher", "a@b.com",
            "--custom-field", "Sprint=1",
            "--template-id", "TPL1",
        ])
        self.assertEqual(args.title, "T")
        self.assertTrue(args.blocked)

    def test_create_cards_alias_parseable(self):
        args = self.parser.parse_args(["create-cards", "--file", "cards.json"])
        self.assertEqual(args.file, "cards.json")

    def test_update_card_alias_parseable(self):
        args = self.parser.parse_args(["update-card", "--id", "42", "--title", "New"])
        self.assertEqual(args.id, "42")
        self.assertEqual(args.title, "New")

    def test_update_card_blocked_field(self):
        args = self.parser.parse_args(["update-card", "--id", "42", "--blocked", "true"])
        self.assertTrue(args.blocked)

    def test_move_card_alias_parseable(self):
        args = self.parser.parse_args([
            "move-card", "--id", "42", "--column-id", "COL2",
        ])
        self.assertEqual(args.id, "42")
        self.assertEqual(args.column_id, "COL2")

    def test_move_card_with_add_to_top(self):
        args = self.parser.parse_args([
            "move-card", "--id", "42", "--column-id", "COL2", "--add-to-top",
        ])
        self.assertTrue(args.add_to_top)

    def test_link_card_card_branch(self):
        args = self.parser.parse_args([
            "link-card", "--id", "42", "--card", "99",
        ])
        self.assertEqual(args.card, 99)
        self.assertIsNone(args.url)

    def test_link_card_url_branch(self):
        args = self.parser.parse_args([
            "link-card", "--id", "42", "--url", "https://spec.example",
            "--title", "Spec", "--type", "external",
        ])
        self.assertEqual(args.url, "https://spec.example")

    def test_unlink_card_alias_parseable(self):
        args = self.parser.parse_args([
            "unlink-card", "--id", "42", "--card", "99",
        ])
        self.assertEqual(args.card, 99)

    def test_search_cards_alias_parseable(self):
        args = self.parser.parse_args(["search-cards", "--query", "deploy"])
        self.assertEqual(args.query, "deploy")

    def test_wip_check_alias_parseable(self):
        args = self.parser.parse_args(["wip-check"])
        self.assertIsNotNone(args.func)

    def test_wrap_boards_get_sets_include_flags(self):
        """_wrap_boards_get should fill in include_members/labels/custom_fields defaults."""
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("GET", "/boards/B1", params={
                "includeColumns": False, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({"publicId": "B1"})
            with patch("sys.stdout", io.StringIO()):
                args = self.parser.parse_args(["board"])
                args.func(args, ctx)

    def test_wrap_boards_list_defaults(self):
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("GET", "/boards", params={
                "includeArchived": False, "includeColumns": False,
            }).returns({"count": 0, "boards": []})
            with patch("sys.stdout", io.StringIO()):
                # boards group falls through to cmd_list which calls _wrap indirectly
                kz_legacy._wrap_boards_list(
                    type("A", (), {"include_archived": False, "include_columns": False})(),
                    ctx,
                )

    def test_wrap_cards_list_fills_defaults(self):
        """_wrap_cards_list uses getattr with defaults for missing attributes."""
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"count": 0, "cards": [], "hasMore": False})
            with patch("sys.stdout", io.StringIO()):
                # Simulate an args object with NO page/count/include_archived attrs
                # so _wrap_cards_list's getattr(args, k, default) falls through.
                class _MinArgs:
                    label = None
                    owner = None
                    column = None
                    priority = None
                    blocked = False
                    query = None
                    days_since_last_update = None
                kz_legacy._wrap_cards_list(_MinArgs(), ctx)

    def test_wrap_cards_get_copies_number_to_id(self):
        CARD_OID = "6700aabbccddeeff00112233"
        ctx = type("C", (), {"pretty": False, "board": "B1",
                              "cache": type("Cch", (), {
                                  "get_card_oid": lambda s, b, n: CARD_OID,
                              })()})()
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {"number": "42"})()
                kz_legacy._wrap_cards_get(args, ctx)

    def test_wrap_cards_create_calls_cmd_create(self):
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={
                "board": "B1", "addToTop": False,
                "cards": [{"title": "T"}],
            }).returns({"cardsAdded": 1, "cards": []})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "title": "T", "description": None, "description_file": None,
                    "column_id": None, "owner": None, "priority": None,
                    "label": None, "size": None, "due_at": None,
                    "blocked": False, "blocked_reason": None,
                    "add_to_top": False, "watcher": [], "custom_field": [],
                    "template_id": None,
                })()
                kz_legacy._wrap_cards_create(args, ctx)

    def test_wrap_cards_create_bulk_calls_cmd(self):
        import json
        import os
        import tempfile
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "c.json")
            with open(fpath, "w") as f:
                json.dump({"board": "B1", "cards": [{"title": "X"}]}, f)
            with FakeApi() as fake:
                fake.expect("POST", "/cards", body={
                    "board": "B1", "cards": [{"title": "X"}],
                }).returns({"cardsAdded": 1, "cards": []})
                with patch("sys.stdout", io.StringIO()):
                    args = type("A", (), {"file": fpath})()
                    kz_legacy._wrap_cards_create_bulk(args, ctx)

    def test_wrap_cards_update_converts_id(self):
        CARD_OID = "6700aabbccddeeff00112233"
        from kz.cache import Cache
        import tempfile, os
        ctx = type("C", (), {
            "pretty": False, "board": "B1",
            "cache": Cache(os.path.join(
                tempfile.mkdtemp(), "c.json"
            )),
        })()
        ctx.cache.set_card_mapping("B1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "B1", "title": "Updated",
            }).returns({"_id": CARD_OID})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "id": 42, "title": "Updated",
                    "description": None, "description_file": None,
                    "owner": None, "priority": None, "label": None,
                    "size": None, "due_at": None, "blocked": None,
                    "blocked_reason": None, "watcher": [], "custom_field": [],
                })()
                kz_legacy._wrap_cards_update(args, ctx)

    def test_wrap_cards_move(self):
        CARD_OID = "6700aabbccddeeff00112233"
        from kz.cache import Cache
        import tempfile, os
        ctx = type("C", (), {
            "pretty": False, "board": "B1",
            "cache": Cache(os.path.join(tempfile.mkdtemp(), "c.json")),
        })()
        ctx.cache.set_card_mapping("B1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", f"/cards/{CARD_OID}/move", body={
                "board": "B1", "columnId": "COL2", "addToTop": False,
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "id": "42", "column_id": "COL2",
                })()
                kz_legacy._wrap_cards_move(args, ctx)

    def test_wrap_cards_links_add(self):
        CARD_OID = "6700aabbccddeeff00112233"
        from kz.cache import Cache
        import tempfile, os
        ctx = type("C", (), {
            "pretty": False, "board": "B1",
            "cache": Cache(os.path.join(tempfile.mkdtemp(), "c.json")),
        })()
        ctx.cache.set_card_mapping("B1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "B1",
                "links": {"add": [{"card": 99, "type": "related"}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "id": "42", "card": 99, "url": None,
                    "title": None, "type": None,
                })()
                kz_legacy._wrap_cards_links_add(args, ctx)

    def test_wrap_cards_links_remove(self):
        CARD_OID = "6700aabbccddeeff00112233"
        from kz.cache import Cache
        import tempfile, os
        ctx = type("C", (), {
            "pretty": False, "board": "B1",
            "cache": Cache(os.path.join(tempfile.mkdtemp(), "c.json")),
        })()
        ctx.cache.set_card_mapping("B1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "B1",
                "links": {"remove": [{"card": 99}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "id": "42", "card": 99, "url": None,
                })()
                kz_legacy._wrap_cards_links_remove(args, ctx)

    def test_wrap_cards_search(self):
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("GET", "/boards", params={"includeArchived": False}).returns({
                "boards": [],
            })
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {
                    "query": None, "label": None, "owner": None,
                })()
                kz_legacy._wrap_cards_search(args, ctx)

    def test_wrap_cards_wip_check(self):
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect("GET", "/boards/B1", params={
                "includeColumns": True, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({"columns": []})
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [], "hasMore": False})
            with patch("sys.stdout", io.StringIO()):
                args = type("A", (), {})()
                kz_legacy._wrap_cards_wip_check(args, ctx)


if __name__ == "__main__":
    unittest.main()
