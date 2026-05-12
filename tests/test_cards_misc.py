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
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardLinks(unittest.TestCase):
    def test_links_add_card(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"add": [{"card": 99, "type": "related"}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_links_add(_ns(
                    id="42", card=99, url=None, title=None, type="related",
                ), ctx)

    def test_links_add_url(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"add": [{"url": "https://x", "title": "Spec",
                                    "type": "external"}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_links_add(_ns(
                    id="42", card=None, url="https://x", title="Spec", type="external",
                ), ctx)

    def test_links_remove_card(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"remove": [{"card": 99}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_cards.cmd_links_remove(_ns(
                    id="42", card=99, url=None,
                ), ctx)


class TestCardsSearch(unittest.TestCase):
    def test_search_iterates_all_boards(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards", params={"includeArchived": False}).returns({
                "boards": [{"publicId": "B1", "name": "One"},
                           {"publicId": "B2", "name": "Two"}],
            })
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"_id": "a" * 24, "CardItem": {"number": 1, "title": "deploy soon"}}],
                        "hasMore": False})
            fake.expect("GET", "/cards", params={
                "board": "B2", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"_id": "b" * 24, "CardItem": {"number": 2, "title": "buy lunch"}}],
                        "hasMore": False})
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kanban_zone_cards.cmd_search(_ns(query="deploy", label=None, owner=None), _Ctx())
            self.assertIn('"deploy soon"', buf.getvalue())
            self.assertNotIn('"buy lunch"', buf.getvalue())


class TestWipCheck(unittest.TestCase):
    def test_wip_check_flags_violations(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1", params={
                "includeColumns": True, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({
                "publicId": "BOARD1",
                "columns": [
                    {"_id": "c1", "title": "Backlog", "minWIP": 0, "maxWIP": 10},
                    {"_id": "c2", "title": "Doing", "minWIP": 1, "maxWIP": 3},
                ],
            })
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "cards": [
                    {"_id": "1" * 24, "CardItem": {"columnId": "c2"}},
                    {"_id": "2" * 24, "CardItem": {"columnId": "c2"}},
                    {"_id": "3" * 24, "CardItem": {"columnId": "c2"}},
                    {"_id": "4" * 24, "CardItem": {"columnId": "c2"}},
                    {"_id": "5" * 24, "CardItem": {"columnId": "c2"}},
                ],
                "hasMore": False,
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kanban_zone_cards.cmd_wip_check(_ns(), _Ctx())
            self.assertIn('"violation"', buf.getvalue())
            self.assertIn('"Doing"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
