import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import tokens as kz_tokens
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"
CARDTOKEN_ID = "9999aaaa8888bbbb7777cccc"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestTokens(unittest.TestCase):
    def test_assign(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/tokens", body={
                "card": CARD_OID, "tokenId": "TKN1", "board": "BOARD1",
            }).returns({"_id": CARDTOKEN_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_assign(_ns(card="42", token_id="TKN1"), ctx)

    def test_revoke(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/tokens/{CARDTOKEN_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_revoke(_ns(id=CARDTOKEN_ID), _Ctx())

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/tokens").returns([])
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_list(_ns(card="42"), ctx)

    def test_resolve_card_requires_board(self):
        """_resolve_card raises ValueError when board is falsy (line 9)."""
        ctx = _Ctx()
        ctx.board = None
        with self.assertRaises(ValueError):
            kz_tokens.cmd_list(_ns(card="42"), ctx)


if __name__ == "__main__":
    unittest.main()
