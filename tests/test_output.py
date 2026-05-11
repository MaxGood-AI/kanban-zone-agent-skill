import io
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import output


class TestPrintJson(unittest.TestCase):
    def test_compact_default(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json({"a": 1, "b": [2, 3]}, pretty=False)
        self.assertEqual(buf.getvalue().strip(), '{"a": 1, "b": [2, 3]}')

    def test_pretty(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json({"a": 1}, pretty=True)
        self.assertIn('  "a": 1', buf.getvalue())

    def test_none_prints_null(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json(None, pretty=False)
        self.assertEqual(buf.getvalue().strip(), "null")


class TestErrorExit(unittest.TestCase):
    def test_writes_json_to_stderr_and_exits_1(self):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            with self.assertRaises(SystemExit) as cm:
                output.error_exit("boom", status=429)
        self.assertEqual(cm.exception.code, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload, {"error": True, "status": 429, "message": "boom"})

    def test_status_optional(self):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            with self.assertRaises(SystemExit):
                output.error_exit("boom")
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload, {"error": True, "message": "boom"})


if __name__ == "__main__":
    unittest.main()
