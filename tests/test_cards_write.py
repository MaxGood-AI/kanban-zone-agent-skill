import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import cards as kz_cards
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardsWrite(unittest.TestCase):
    def test_create_minimal(self):
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={
                "board": "BOARD1", "addToTop": False,
                "cards": [{"title": "X"}],
            }).returns({"cardsAdded": 1, "cards": [{"_id": CARD_OID, "number": 7}]})
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_create(_ns(
                    title="X", description=None, description_file=None,
                    column_id=None, owner=None, priority=None, label=None,
                    size=None, due_at=None, blocked=False, blocked_reason=None,
                    add_to_top=False, watcher=[], custom_field=[], template_id=None,
                ), _Ctx())
            self.assertIn('"cardsAdded": 1', buf.getvalue())

    def test_create_with_watchers_and_custom_fields(self):
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={
                "board": "BOARD1", "addToTop": True,
                "cards": [{
                    "title": "X", "watchers": ["a@b.com", "c@d.com"],
                    "customFields": [{"label": "Sprint", "value": "42"}],
                }],
            }).returns({"cardsAdded": 1, "cards": []})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_create(_ns(
                    title="X", description=None, description_file=None,
                    column_id=None, owner=None, priority=None, label=None,
                    size=None, due_at=None, blocked=False, blocked_reason=None,
                    add_to_top=True, watcher=["a@b.com", "c@d.com"],
                    custom_field=["Sprint=42"], template_id=None,
                ), _Ctx())

    def test_create_bulk_from_file(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "cards.json")
            with open(fpath, "w") as f:
                json.dump({"board": "BOARD1", "cards": [{"title": "A"}, {"title": "B"}]}, f)
            with FakeApi() as fake:
                fake.expect("POST", "/cards", body={
                    "board": "BOARD1", "cards": [{"title": "A"}, {"title": "B"}],
                }).returns({"cardsAdded": 2, "cards": []})
                with patch("sys.stdout", io.StringIO()):
                    kz_cards.cmd_create_bulk(_ns(file=fpath), _Ctx())

    def test_update_uses_patch_after_resolution(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1", "title": "New",
            }).returns({"_id": CARD_OID, "number": 42, "title": "New"})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_update(_ns(
                    id="42", title="New", description=None, description_file=None,
                    owner=None, priority=None, label=None, size=None, due_at=None,
                    blocked=None, blocked_reason=None, watcher=[], custom_field=[],
                ), ctx)

    def test_update_blocked_true_includes_reason(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1", "blocked": True, "blockedReason": "waiting",
            }).returns({"_id": CARD_OID})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_update(_ns(
                    id="42", title=None, description=None, description_file=None,
                    owner=None, priority=None, label=None, size=None, due_at=None,
                    blocked=True, blocked_reason="waiting", watcher=[], custom_field=[],
                ), ctx)

    def test_move_uses_post_move(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", f"/cards/{CARD_OID}/move", body={
                "board": "BOARD1", "columnId": "COL2", "addToTop": False,
            }).returns({"_id": CARD_OID, "columnId": "COL2"})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_move(_ns(id="42", column_id="COL2", add_to_top=False), ctx)

    def test_delete_invalidates_cache(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("DELETE", f"/cards/{CARD_OID}",
                        params={"board": "BOARD1"}).returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_delete(_ns(id="42"), ctx)
        self.assertIsNone(ctx.cache.get_card_oid("BOARD1", 42))

    def test_parse_custom_fields_bad_format_raises(self):
        """_parse_custom_fields raises ValueError for entries without '=' (lines 96)."""
        with self.assertRaises(ValueError):
            kz_cards._parse_custom_fields(["BadFormatNoEquals"])

    def test_read_description_from_file(self):
        """_read_description reads from description_file when set (lines 104-105)."""
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "desc.txt")
            with open(fpath, "w") as f:
                f.write("file content")
            args = _ns(description_file=fpath, description=None)
            result = kz_cards._read_description(args)
        self.assertEqual(result, "file content")

    def test_card_input_includes_all_optional_fields(self):
        """_card_input maps all optional fields into the body dict (line 115-129)."""
        args = _ns(
            title="T", description_file=None, description="D",
            column_id="COL1", owner="alice", priority="high",
            label="Bug", size="3", due_at="2026-12-31",
            blocked=True, blocked_reason="waiting",
            watcher=["a@b.com"], custom_field=["Sprint=1"],
            template_id="TPL1",
        )
        body = kz_cards._card_input(args, include_title=True)
        self.assertEqual(body["title"], "T")
        self.assertEqual(body["description"], "D")
        self.assertEqual(body["columnId"], "COL1")
        self.assertEqual(body["owner"], "alice")
        self.assertEqual(body["priority"], "high")
        self.assertEqual(body["label"], "Bug")
        self.assertEqual(body["size"], "3")
        self.assertEqual(body["dueAt"], "2026-12-31")
        self.assertTrue(body["blocked"])
        self.assertEqual(body["blockedReason"], "waiting")
        self.assertEqual(body["watchers"], ["a@b.com"])
        self.assertEqual(body["customFields"], [{"label": "Sprint", "value": "1"}])
        self.assertEqual(body["templateId"], "TPL1")

    def test_card_input_blocked_false_not_included(self):
        """When blocked=False (from update form), 'blocked' is NOT added to body (line 129)."""
        args = _ns(
            title=None, description_file=None, description=None,
            column_id=None, owner=None, priority=None, label=None,
            size=None, due_at=None, blocked=False, blocked_reason=None,
            watcher=[], custom_field=[], template_id=None,
        )
        body = kz_cards._card_input(args, include_title=False)
        self.assertNotIn("blocked", body)

    def test_create_bulk_uses_board_from_ctx_when_missing(self):
        """create_bulk injects board from ctx when not present in JSON (line 150)."""
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "cards.json")
            with open(fpath, "w") as f:
                json.dump({"cards": [{"title": "X"}]}, f)
            with FakeApi() as fake:
                fake.expect("POST", "/cards", body={
                    "board": "BOARD1", "cards": [{"title": "X"}],
                }).returns({"cardsAdded": 1, "cards": []})
                with patch("sys.stdout", io.StringIO()):
                    kz_cards.cmd_create_bulk(_ns(file=fpath), _Ctx())

    def test_links_payload_raises_when_neither_card_nor_url(self):
        """_links_payload raises ValueError when neither --card nor --url given (line 193)."""
        args = _ns(card=None, url=None, title=None, type=None)
        with self.assertRaises(ValueError):
            kz_cards._links_payload("add", args)

    def test_links_remove_url_branch(self):
        """_links_payload remove with URL builds remove payload (lines 189-192)."""
        args = _ns(card=None, url="https://x", title=None, type=None)
        payload = kz_cards._links_payload("remove", args)
        self.assertEqual(payload, {"remove": [{"url": "https://x"}]})

    def test_fetch_all_cards_pagination(self):
        """_fetch_all_cards follows hasMore pagination (lines 213-223)."""
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"number": 1}], "hasMore": True})
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 2, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"number": 2}], "hasMore": False})
            result = kz_cards._fetch_all_cards("B1")
        self.assertEqual([c["number"] for c in result], [1, 2])

    def test_wip_check_below_min_status(self):
        """cmd_wip_check flags columns with fewer cards than minWIP (line 266)."""
        ctx = _Ctx()
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1", params={
                "includeColumns": True, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({
                "columns": [
                    {"_id": "c1", "title": "Doing", "minWIP": 3, "maxWIP": 5},
                ],
            })
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"columnId": "c1"}], "hasMore": False})
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_wip_check(_ns(), ctx)
        self.assertIn('"below_min"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
