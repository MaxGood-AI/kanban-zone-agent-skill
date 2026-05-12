import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import checklists as kanban_zone_chk
from kanban_zone.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"
CHK_ID = "abcd1234ef5678901234abcd"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestChecklists(unittest.TestCase):
    def test_create_minimal(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/checklists", body={
                "card": CARD_OID, "title": "Pre-flight",
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_create(_ns(card="42", title="Pre-flight", task=[]), ctx)

    def test_create_with_inline_tasks(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/checklists", body={
                "card": CARD_OID, "title": "QA",
                "tasks": [{"description": "First"}, {"description": "Second"}],
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_create(_ns(
                    card="42", title="QA", task=["First", "Second"],
                ), ctx)

    def test_update_renames(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/checklists/{CHK_ID}", body={
                "title": "Renamed",
            }).returns({"_id": CHK_ID, "title": "Renamed"})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_update(_ns(id=CHK_ID, title="Renamed", position=None), _Ctx())

    def test_update_position(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/checklists/{CHK_ID}", body={
                "position": 1,
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_update(_ns(id=CHK_ID, title=None, position=1), _Ctx())

    def test_delete(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/checklists/{CHK_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_delete(_ns(id=CHK_ID), _Ctx())

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/checklists").returns([])
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_chk.cmd_list(_ns(card="42"), ctx)

    def test_resolve_card_requires_board(self):
        """_resolve_card raises ValueError when board is falsy (line 9)."""
        ctx = _Ctx()
        ctx.board = None
        with self.assertRaises(ValueError):
            kanban_zone_chk.cmd_create(_ns(card="42", title="T", task=[]), ctx)

    def test_update_no_body_raises(self):
        """cmd_update raises ValueError when neither --title nor --position given (line 29)."""
        with self.assertRaises(ValueError):
            kanban_zone_chk.cmd_update(_ns(id=CHK_ID, title=None, position=None), _Ctx())


if __name__ == "__main__":
    unittest.main()
