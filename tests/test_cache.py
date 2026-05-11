import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
from kz.cache import Cache


class TestCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "cache.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_missing_file_returns_empty(self):
        c = Cache(self.path)
        self.assertEqual(c.get_board("XYZ"), None)

    def test_set_then_get_board(self):
        c = Cache(self.path)
        c.set_board("XYZ", "My Board")
        self.assertEqual(c.get_board("XYZ"), {"name": "My Board"})

    def test_set_and_get_columns(self):
        c = Cache(self.path)
        c.set_columns("XYZ", {"col1": {"name": "Backlog", "state": "Backlog"}})
        self.assertEqual(c.get_column("XYZ", "col1"), {"name": "Backlog", "state": "Backlog"})

    def test_card_mapping_bidirectional(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        self.assertEqual(c.get_card_oid("XYZ", 42), "6700aabbccddeeff00112233")
        self.assertEqual(c.get_card_number("XYZ", "6700aabbccddeeff00112233"), 42)

    def test_invalidate_card_removes_both_directions(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        c.invalidate_card("XYZ", 42)
        self.assertIsNone(c.get_card_oid("XYZ", 42))
        self.assertIsNone(c.get_card_number("XYZ", "6700aabbccddeeff00112233"))

    def test_invalidate_card_by_oid(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        c.invalidate_card("XYZ", "6700aabbccddeeff00112233")
        self.assertIsNone(c.get_card_oid("XYZ", 42))
        self.assertIsNone(c.get_card_number("XYZ", "6700aabbccddeeff00112233"))

    def test_flush_persists_to_disk_atomically(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 1, "a" * 24)
        c.flush()
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["boards"]["XYZ"]["cards"]["byNumber"]["1"], "a" * 24)

    def test_load_v2_format_without_cards_block(self):
        # v2 cache file lacking the cards block must still load
        with open(self.path, "w") as f:
            json.dump({
                "boards": {"XYZ": {"name": "Old Board", "columns": {}}},
                "updated": "2024-01-01T00:00:00Z",
            }, f)
        c = Cache(self.path)
        self.assertEqual(c.get_board("XYZ"), {"name": "Old Board"})
        self.assertIsNone(c.get_card_oid("XYZ", 1))

    def test_no_op_cache_disables_persistence(self):
        c = Cache(self.path, enabled=False)
        c.set_card_mapping("XYZ", 1, "a" * 24)
        c.flush()
        self.assertFalse(os.path.exists(self.path))
        # but in-memory still works for the lifetime of the object
        self.assertEqual(c.get_card_oid("XYZ", 1), "a" * 24)

    def test_updated_timestamp_set_on_flush(self):
        c = Cache(self.path)
        c.set_board("XYZ", "B")
        c.flush()
        with open(self.path) as f:
            data = json.load(f)
        self.assertIn("updated", data)
        self.assertTrue(data["updated"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
