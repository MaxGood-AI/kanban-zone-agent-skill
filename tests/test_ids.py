import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
from kz import ids
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class TestDetectIdKind(unittest.TestCase):
    def test_pure_digits_is_number(self):
        self.assertEqual(ids.detect_id_kind("42"), "number")

    def test_24_hex_is_object_id(self):
        self.assertEqual(ids.detect_id_kind(CARD_OID), "object_id")

    def test_24_hex_uppercase_is_object_id(self):
        self.assertEqual(ids.detect_id_kind(CARD_OID.upper()), "object_id")

    def test_short_hex_raises(self):
        with self.assertRaises(ids.KZIdError):
            ids.detect_id_kind("abc123")

    def test_empty_raises(self):
        with self.assertRaises(ids.KZIdError):
            ids.detect_id_kind("")


class TestResolveCardObjectId(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_object_id_passthrough(self):
        with FakeApi() as fake:
            result = ids.resolve_card_object_id(CARD_OID, "BOARD1", self.cache)
            self.assertEqual(result, CARD_OID)
            fake.assert_no_more_calls()

    def test_number_with_cache_hit_returns_without_api_call(self):
        self.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            result = ids.resolve_card_object_id("42", "BOARD1", self.cache)
            self.assertEqual(result, CARD_OID)
            fake.assert_no_more_calls()

    def test_number_cache_miss_pages_until_match_then_caches(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 5, "hasMore": True,
                "cards": [
                    {"_id": "a" * 24, "number": 7, "title": "x"},
                    {"_id": "b" * 24, "number": 8, "title": "x"},
                ],
            })
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 2, "count": 100, "includeArchived": False,
            }).returns({
                "count": 3, "totalAvailable": 5, "hasMore": False,
                "cards": [
                    {"_id": "c" * 24, "number": 41, "title": "x"},
                    {"_id": CARD_OID, "number": 42, "title": "x"},
                    {"_id": "d" * 24, "number": 43, "title": "x"},
                ],
            })
            result = ids.resolve_card_object_id("42", "BOARD1", self.cache)
        self.assertEqual(result, CARD_OID)
        self.assertEqual(self.cache.get_card_oid("BOARD1", 42), CARD_OID)
        self.assertEqual(self.cache.get_card_number("BOARD1", CARD_OID), 42)

    def test_number_not_found_raises(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"count": 0, "totalAvailable": 0, "hasMore": False, "cards": []})
            with self.assertRaises(ids.KZIdError):
                ids.resolve_card_object_id("999", "BOARD1", self.cache)


class TestResolveCardNumber(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_number_passthrough(self):
        with FakeApi() as fake:
            self.assertEqual(ids.resolve_card_number("42", "B", self.cache), 42)
            fake.assert_no_more_calls()

    def test_object_id_cache_hit(self):
        self.cache.set_card_mapping("B", 42, CARD_OID)
        with FakeApi() as fake:
            self.assertEqual(ids.resolve_card_number(CARD_OID, "B", self.cache), 42)
            fake.assert_no_more_calls()

    def test_object_id_cache_miss_fetches_card(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns(
                {"_id": CARD_OID, "number": 42, "title": "x"}
            )
            self.assertEqual(ids.resolve_card_number(CARD_OID, "B", self.cache), 42)
            self.assertEqual(self.cache.get_card_oid("B", 42), CARD_OID)


if __name__ == "__main__":
    unittest.main()
