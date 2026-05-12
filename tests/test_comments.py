import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import comments as kz_comments
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


class TestComments(unittest.TestCase):
    def test_add_resolves_card_and_uses_flat_url(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/comments", body={
                "card": CARD_OID, "text": "hello",
            }).returns({"_id": "C1"})
            with patch("sys.stdout", io.StringIO()):
                kz_comments.cmd_add(_ns(card="42", text="hello", text_file=None), ctx)

    def test_add_text_from_file(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "t.txt")
            with open(f, "w") as fh:
                fh.write("from file")
            with FakeApi() as fake:
                fake.expect("POST", "/comments", body={
                    "card": CARD_OID, "text": "from file",
                }).returns({"_id": "C1"})
                with patch("sys.stdout", io.StringIO()):
                    kz_comments.cmd_add(_ns(card="42", text=None, text_file=f), ctx)

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/comments").returns([{"_id": "C1"}])
            with patch("sys.stdout", io.StringIO()):
                kz_comments.cmd_list(_ns(card="42"), ctx)

    def test_add_requires_text_or_file(self):
        ctx = _Ctx()
        with self.assertRaises(ValueError):
            kz_comments.cmd_add(_ns(card="42", text=None, text_file=None), ctx)

    def test_resolve_requires_board(self):
        """_resolve raises ValueError when board is falsy (line 9)."""
        ctx = _Ctx()
        ctx.board = None
        with self.assertRaises(ValueError):
            kz_comments.cmd_list(_ns(card="42"), ctx)


if __name__ == "__main__":
    unittest.main()
