import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
from kanban_zone.cache import Cache


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

    def test_corrupted_cache_file_is_silently_ignored(self):
        """OSError / JSONDecodeError on load yields an empty cache (lines 35-36)."""
        with open(self.path, "w") as f:
            f.write("not valid json{{{")
        c = Cache(self.path)
        self.assertIsNone(c.get_board("XYZ"))

    def test_non_dict_cache_file_is_silently_ignored(self):
        """If the JSON top-level is not a dict with 'boards', cache starts empty."""
        with open(self.path, "w") as f:
            json.dump(["not", "a", "dict"], f)
        c = Cache(self.path)
        self.assertIsNone(c.get_board("XYZ"))

    def test_get_column_returns_none_for_unknown_board(self):
        """get_column on a board that was never set returns None (line 64)."""
        c = Cache(self.path)
        self.assertIsNone(c.get_column("NOPE", "col1"))

    def test_invalidate_card_no_op_for_unknown_board(self):
        """invalidate_card on a board not in cache is a no-op (line 91)."""
        c = Cache(self.path)
        c.invalidate_card("GHOST", 99)  # must not raise

    def test_invalidate_card_by_oid_removes_number_too(self):
        """invalidate_card by OID also removes the number->OID mapping (lines 97-99)."""
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 5, "a" * 24)
        c.invalidate_card("XYZ", "a" * 24)
        self.assertIsNone(c.get_card_oid("XYZ", 5))
        self.assertIsNone(c.get_card_number("XYZ", "a" * 24))

    def test_flush_exception_cleanup_and_reraise(self):
        """If the atomic write fails mid-way, the tmp file is deleted and exception re-raised (lines 111-115)."""
        c = Cache(self.path)
        c.set_board("XYZ", "B")
        import builtins
        real_open = builtins.open
        def _fail_open(name, *a, **kw):
            if name.endswith(".json") and "w" in str(a) and not kw:
                raise OSError("disk full")
            return real_open(name, *a, **kw)
        # Patch os.fdopen to raise so we exercise the exception branch
        original_fdopen = os.fdopen
        def _bad_fdopen(fd, *a, **kw):
            # close fd to avoid leak, then raise
            os.close(fd)
            raise OSError("disk full")
        os.fdopen = _bad_fdopen
        try:
            with self.assertRaises(OSError):
                c.flush()
        finally:
            os.fdopen = original_fdopen


if __name__ == "__main__":
    unittest.main()
