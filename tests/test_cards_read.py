import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import cards as kanban_zone_cards
from kanban_zone.cache import Cache
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
                kanban_zone_cards.cmd_list(_ns(
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
                kanban_zone_cards.cmd_list(_ns(
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
                    {"_id": "a" * 24, "CardItem": {"number": 1, "label": "Bug", "title": "x"}},
                    {"_id": "b" * 24, "CardItem": {"number": 2, "label": "Feature", "title": "y"}},
                ],
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kanban_zone_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label="Bug", owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())
        self.assertIn('"number": 1', buf.getvalue())
        self.assertNotIn('"number": 2', buf.getvalue())

    def test_list_client_side_filter_envelope_form(self):
        """_filter_cards matches label inside the v1.4 CardItem envelope."""
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 2, "hasMore": False,
                "cards": [
                    {"_id": "a" * 24, "CardItem": {"number": 10, "label": "Bug", "title": "fix"}},
                    {"_id": "b" * 24, "CardItem": {"number": 11, "label": "Feature", "title": "add"}},
                ],
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kanban_zone_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label="Bug", owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())
        out = buf.getvalue()
        self.assertIn('"number": 10', out)
        self.assertNotIn('"number": 11', out)

    def test_get_by_number_resolves_then_calls_oid_endpoint(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_get(_ns(id="42"), ctx)

    def test_get_by_object_id_skips_resolution(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_get(_ns(id=CARD_OID), _Ctx())

    def test_history_uses_oid_and_passes_from(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/history",
                        params={"from": "2025-01-01"}).returns([])
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_history(_ns(id="42", from_date="2025-01-01"), ctx)

    def test_metrics_uses_oid(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/metrics").returns({"cycle": 1.5})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_metrics(_ns(id="42"), ctx)

    def test_require_board_raises_when_board_missing(self):
        """_require_board raises ValueError when ctx.board is falsy (line 12)."""
        ctx = _Ctx(board=None)
        with self.assertRaises(ValueError):
            kanban_zone_cards.cmd_list(_ns(
                page=1, count=100, include_archived=False, days_since_last_update=None,
                label=None, owner=None, column=None, priority=None, blocked=False, query=None,
            ), ctx)

    def test_history_without_from_date(self):
        """cmd_history with no from_date omits the params entirely (line 80->82)."""
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/history", params=None).returns([])
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_history(_ns(id="42", from_date=None), ctx)

    def test_filter_cards_by_column(self):
        """_filter_cards column match uses columnTitle or column field (line 33-36)."""
        cards = [
            {"number": 1, "columnTitle": "Doing", "title": "a"},
            {"number": 2, "column": "Done", "title": "b"},
            {"number": 3, "columnTitle": "Backlog", "title": "c"},
        ]
        result = kanban_zone_cards._filter_cards(cards, column="Doing")
        self.assertEqual([c["number"] for c in result], [1])

    def test_filter_cards_by_priority(self):
        """_filter_cards priority uses str comparison (line 38)."""
        cards = [
            {"number": 1, "priority": 1},
            {"number": 2, "priority": 2},
        ]
        result = kanban_zone_cards._filter_cards(cards, priority="1")
        self.assertEqual([c["number"] for c in result], [1])

    def test_filter_cards_by_query(self):
        """_filter_cards query searches title+description (lines 41-44)."""
        cards = [
            {"number": 1, "title": "Deploy service", "description": ""},
            {"number": 2, "title": "Buy groceries", "description": ""},
        ]
        result = kanban_zone_cards._filter_cards(cards, query="deploy")
        self.assertEqual([c["number"] for c in result], [1])

    def test_filter_cards_multiple_combined(self):
        """_filter_cards with multiple filters combined (label + owner + blocked)."""
        cards = [
            {"number": 1, "label": "Bug", "owner": "alice", "blocked": True},
            {"number": 2, "label": "Bug", "owner": "bob", "blocked": True},
            {"number": 3, "label": "Feature", "owner": "alice", "blocked": True},
            {"number": 4, "label": "Bug", "owner": "alice", "blocked": False},
        ]
        result = kanban_zone_cards._filter_cards(cards, label="Bug", owner="alice", blocked=True)
        self.assertEqual([c["number"] for c in result], [1])

    def test_get_field_returns_custom_value(self):
        """_get_field falls back to card['custom'] dict (line 23)."""
        card = {"custom": {"sprint": "42"}}
        val = kanban_zone_cards._get_field(card, "sprint")
        self.assertEqual(val, "42")

    def test_get_field_returns_none_for_missing(self):
        """_get_field returns None when neither direct nor custom field exists."""
        card = {}
        val = kanban_zone_cards._get_field(card, "nonexistent")
        self.assertIsNone(val)

    def test_list_with_filter_no_api_filters(self):
        """cmd_list activates client filter when blocked=True (line 59 branch)."""
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 2, "hasMore": False,
                "cards": [
                    {"number": 1, "owner": "alice", "blocked": True},
                    {"number": 2, "owner": "alice", "blocked": False},
                ],
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kanban_zone_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label=None, owner=None, column=None, priority=None, blocked=True, query=None,
                ), _Ctx())
        out = buf.getvalue()
        self.assertIn('"number": 1', out)
        self.assertNotIn('"number": 2', out)


if __name__ == "__main__":
    unittest.main()
