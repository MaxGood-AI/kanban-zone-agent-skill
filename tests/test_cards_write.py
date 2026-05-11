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


if __name__ == "__main__":
    unittest.main()
