import io
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
    def __init__(self, board="BOARD1"):
        self.board = board
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardsRead(unittest.TestCase):
    def test_list_default_filters(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"count": 0, "cards": [], "hasMore": False, "totalAvailable": 0})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label=None, owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())

    def test_list_passes_days_since_last_update(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100,
                "includeArchived": False, "daysSinceLastUpdate": 7,
            }).returns({"count": 0, "cards": [], "hasMore": False, "totalAvailable": 0})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=7,
                    label=None, owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())

    def test_list_client_side_filter_by_label(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 2, "hasMore": False,
                "cards": [
                    {"number": 1, "label": "Bug", "title": "x"},
                    {"number": 2, "label": "Feature", "title": "y"},
                ],
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label="Bug", owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())
        self.assertIn('"number": 1', buf.getvalue())
        self.assertNotIn('"number": 2', buf.getvalue())

    def test_get_by_number_resolves_then_calls_oid_endpoint(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_get(_ns(id="42"), ctx)

    def test_get_by_object_id_skips_resolution(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_get(_ns(id=CARD_OID), _Ctx())

    def test_history_uses_oid_and_passes_from(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/history",
                        params={"from": "2025-01-01"}).returns([])
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_history(_ns(id="42", from_date="2025-01-01"), ctx)

    def test_metrics_uses_oid(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/metrics").returns({"cycle": 1.5})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_metrics(_ns(id="42"), ctx)


if __name__ == "__main__":
    unittest.main()
