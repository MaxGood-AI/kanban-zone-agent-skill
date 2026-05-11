import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")


def run(*args, env_extra=None):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        env=env, capture_output=True, text=True,
    )


class TestSkeleton(unittest.TestCase):
    def test_no_args_prints_help_exit_2(self):
        r = run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage:", r.stderr.lower() + r.stdout.lower())

    def test_help_lists_global_flags(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--board", r.stdout)
        self.assertIn("--no-cache", r.stdout)
        self.assertIn("--pretty", r.stdout)
        self.assertIn("--api-token", r.stdout)


if __name__ == "__main__":
    unittest.main()
