import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")


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


if __name__ == "__main__":
    unittest.main()
