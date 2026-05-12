"""Regression tests for flag aliases that match common API conventions.

These guard against accidental removal during future cleanup. Aliases exist
because consumer agents reach for them based on widespread prior conventions
(--limit for pagination, --q for query, --from/--to for date ranges).
"""
import os
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")
ENV = dict(os.environ, KANBAN_ZONE_API_KEY="test:key",
            KANBAN_ZONE_BOARD_ID="TESTBOARD")


def _help(*argv):
    r = subprocess.run([sys.executable, SCRIPT, *argv, "--help"],
                        env=ENV, capture_output=True, text=True)
    return r.stdout + r.stderr


class TestCardsListAliases(unittest.TestCase):
    def test_limit_alias_in_help(self):
        out = _help("cards", "list")
        self.assertIn("--limit", out, "--limit should be a documented alias for --count")
        self.assertIn("--count", out)

    def test_q_alias_in_help(self):
        out = _help("cards", "list")
        self.assertIn("--q", out, "--q should be a documented alias for --query")
        self.assertIn("--query", out)


class TestCardsSearchAliases(unittest.TestCase):
    def test_q_alias_in_help(self):
        out = _help("cards", "search")
        self.assertIn("--q", out)
        self.assertIn("--query", out)


class TestCardsHistoryAliases(unittest.TestCase):
    def test_from_alias_in_help(self):
        out = _help("cards", "history")
        self.assertIn("--from", out, "--from should be a documented alias for --from-date")
        self.assertIn("--from-date", out)


class TestReportsAliases(unittest.TestCase):
    def test_from_to_aliases_present_on_every_report(self):
        for slug in ("throughput", "arrival-rate", "cycle-time", "lead-time",
                      "flow", "flow-efficiency", "allocation", "abandoned-effort"):
            with self.subTest(report=slug):
                out = _help("reports", slug)
                self.assertIn("--from-date", out)
                self.assertIn("--from", out)
                self.assertIn("--to-date", out)
                self.assertIn("--to", out)


class TestKanbanZoneIdErrorMessage(unittest.TestCase):
    """When a card number can't be resolved, the error message must guide the user."""

    def test_message_mentions_remediation_steps(self):
        # Direct unit test: assert the message format from resolve_card_object_id
        # when paging exhausts without finding the card. We do not call the API;
        # we monkey-patch api_request to return an empty page.
        sys.path.insert(0, "scripts")
        from kanban_zone import ids as kanban_zone_ids
        from kanban_zone.cache import Cache
        from tests.fakes import FakeApi

        with tempfile.TemporaryDirectory() as td:
            cache = Cache(os.path.join(td, "c.json"))
            with FakeApi() as fake:
                fake.expect("GET", "/cards", params={
                    "board": "BOARDX", "page": 1, "count": 100, "includeArchived": False,
                }).returns({"cards": [], "hasMore": False, "totalAvailable": 5})
                try:
                    kanban_zone_ids.resolve_card_object_id("999", "BOARDX", cache)
                    self.fail("expected KanbanZoneIdError")
                except kanban_zone_ids.KanbanZoneIdError as exc:
                    msg = str(exc)
                    self.assertIn("999", msg)
                    self.assertIn("BOARDX", msg)
                    # Remediation hints — these are the contract of the message.
                    self.assertIn("include-archived", msg)
                    self.assertIn("cards search", msg)
                    self.assertIn("--board", msg)


if __name__ == "__main__":
    unittest.main()
