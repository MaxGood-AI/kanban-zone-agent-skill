import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")
GROUPS_AND_SUBCOMMANDS = {
    "boards": ["list", "get", "columns", "labels", "members",
                "custom-fields", "templates"],
    "cards": ["list", "get", "create", "create-bulk", "update", "move",
              "delete", "history", "metrics", "links-add", "links-remove",
              "search", "wip-check"],
    "comments": ["add", "list"],
    "checklists": ["create", "update", "delete", "list"],
    "tasks": ["create", "update", "delete", "move"],
    "webhooks": ["list", "get", "create", "update", "delete", "test",
                 "verify-signature"],
    "reports": ["throughput", "arrival-rate", "cycle-time", "lead-time",
                "flow", "flow-efficiency", "allocation", "abandoned-effort"],
    "tokens": ["assign", "revoke", "list"],
    "org": ["me", "context"],
}


def run(*args):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    return subprocess.run([sys.executable, SCRIPT, *args], env=env,
                            capture_output=True, text=True)


class TestRootHelp(unittest.TestCase):
    def test_each_group_appears(self):
        out = run("--help").stdout
        for group in GROUPS_AND_SUBCOMMANDS:
            self.assertIn(group, out)

    def test_global_flags(self):
        out = run("--help").stdout
        for flag in ["--board", "--no-cache", "--pretty", "--api-token"]:
            self.assertIn(flag, out)


class TestGroupHelp(unittest.TestCase):
    def test_each_group_lists_its_subcommands(self):
        for group, subs in GROUPS_AND_SUBCOMMANDS.items():
            with self.subTest(group=group):
                out = run(group, "--help").stdout
                for sub in subs:
                    self.assertIn(sub, out, f"{group}: missing {sub}")


if __name__ == "__main__":
    unittest.main()
