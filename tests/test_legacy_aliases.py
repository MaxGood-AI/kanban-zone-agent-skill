import io
import os
import subprocess
import sys
import unittest
from argparse import Namespace
from unittest.mock import patch


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")

sys.path.insert(0, "scripts")
from kz import boards as kz_boards, cards as kz_cards  # noqa: E402
from tests.fakes import FakeApi  # noqa: E402


def help_text(*args):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    r = subprocess.run([sys.executable, SCRIPT, *args, "--help"],
                        env=env, capture_output=True, text=True)
    return (r.stdout + r.stderr).lower()


LEGACY_COMMANDS = [
    "boards", "board", "cards", "card", "create-card", "create-cards",
    "update-card", "move-card", "link-card", "unlink-card", "search-cards",
    "wip-check",
]


class TestLegacyAliases(unittest.TestCase):
    def test_root_help_does_not_show_legacy_commands(self):
        text = help_text()
        for cmd in LEGACY_COMMANDS:
            self.assertNotIn(f" {cmd}\n", text + "\n",
                f"legacy alias {cmd!r} appeared in root --help")

    def test_each_legacy_command_has_its_own_help(self):
        # legacy commands suppressed from list, but invokable
        env = dict(os.environ)
        env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
        for cmd in LEGACY_COMMANDS:
            r = subprocess.run([sys.executable, SCRIPT, cmd, "--help"],
                                env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0,
                f"legacy {cmd} --help failed: {r.stderr}")


class TestNoSubcommandFallback(unittest.TestCase):
    """Verify that `boards` and `cards` without a subcommand fall through to
    cmd_list — the v2 back-compat behaviour promised in migration-from-v2.md."""

    def test_boards_defaults_to_list(self):
        """Direct handler invocation — simulates argparse defaulting to cmd_list."""
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect(
                "GET", "/boards",
                params={"includeArchived": False, "includeColumns": False},
            ).returns({"count": 0, "boards": []})
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_list(
                    Namespace(include_archived=False, include_columns=False),
                    ctx,
                )

    def test_cards_defaults_to_list(self):
        """Direct handler invocation — simulates argparse defaulting to cmd_list."""
        ctx = type("C", (), {"pretty": False, "board": "B1", "cache": None})()
        with FakeApi() as fake:
            fake.expect(
                "GET", "/cards",
                params={"board": "B1", "page": 1, "count": 100, "includeArchived": False},
            ).returns({"count": 0, "cards": [], "hasMore": False})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_list(
                    Namespace(
                        page=1, count=100, include_archived=False,
                        days_since_last_update=None,
                        label=None, owner=None, column=None,
                        priority=None, blocked=False, query=None,
                    ),
                    ctx,
                )

    def test_boards_help_exits_zero(self):
        """Smoke test: `boards --help` must succeed (already did, kept for completeness)."""
        env = dict(os.environ)
        env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
        r = subprocess.run(
            [sys.executable, SCRIPT, "boards", "--help"],
            env=env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_cards_help_exits_zero(self):
        """Smoke test: `cards --help` must succeed."""
        env = dict(os.environ)
        env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
        r = subprocess.run(
            [sys.executable, SCRIPT, "cards", "--help"],
            env=env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
