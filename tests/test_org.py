import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import org as kz_org
from tests.fakes import FakeApi


class _StubCtx:
    def __init__(self, pretty=False):
        self.pretty = pretty
        self.board = "BOARDX"
        self.cache = None


class TestOrg(unittest.TestCase):
    def test_me_calls_get_me_and_prints(self):
        buf = io.StringIO()
        with FakeApi() as fake, patch("sys.stdout", buf):
            fake.expect("GET", "/me").returns({"organization": "Acme"})
            kz_org.cmd_me(args=None, ctx=_StubCtx())
        self.assertIn('"organization": "Acme"', buf.getvalue())

    def test_context_sends_include_flags(self):
        buf = io.StringIO()
        ns = type("N", (), {
            "include_boards": True, "include_members": False,
            "include_columns": False, "include_labels": False,
            "include_custom_fields": True,
        })()
        with FakeApi() as fake, patch("sys.stdout", buf):
            fake.expect("GET", "/organization", params={
                "includeBoards": True, "includeMembers": False,
                "includeColumns": False, "includeLabels": False,
                "includeCustomFields": True,
            }).returns({"name": "Acme"})
            kz_org.cmd_context(args=ns, ctx=_StubCtx())
        self.assertIn('"name": "Acme"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
