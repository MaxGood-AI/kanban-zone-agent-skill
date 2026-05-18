import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
import kanban_zone_api


def _real(p):
    return os.path.realpath(p)


class TestEnvDiscovery(unittest.TestCase):
    def test_search_dirs_walk_cwd_ancestors(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = os.path.join(tmp, "a", "b", "c")
            os.makedirs(deep)
            orig_cwd = os.getcwd()
            os.chdir(deep)
            try:
                dirs = [_real(d) for d in kanban_zone_api._env_search_dirs()]
            finally:
                os.chdir(orig_cwd)
            # The cwd and every ancestor up to the root are searched, so a
            # workspace-root .env is found regardless of where the CLI runs.
            self.assertIn(_real(deep), dirs)
            self.assertIn(_real(tmp), dirs)
            self.assertIn(_real(os.path.dirname(deep)), dirs)

    def test_search_dirs_include_script_location(self):
        # The script's own (symlink-resolved) directory must be searched too,
        # so the .env is found even when the cwd is unrelated.
        dirs = [_real(d) for d in kanban_zone_api._env_search_dirs()]
        self.assertIn(_real(kanban_zone_api.REAL_HERE), dirs)

    def test_load_env_finds_dot_env_in_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, ".env"), "w") as f:
                f.write('KZ_TEST_TOKEN="abc123"\n')
            deep = os.path.join(tmp, "x", "y")
            os.makedirs(deep)
            orig_cwd = os.getcwd()
            orig_real = kanban_zone_api.REAL_HERE
            had_before = "KZ_TEST_TOKEN" in os.environ
            os.chdir(deep)
            # Point REAL_HERE at a .env-free tree so the assertion is only
            # about the cwd-ancestor walk, not the real workspace .env.
            kanban_zone_api.REAL_HERE = deep
            try:
                os.environ.pop("KZ_TEST_TOKEN", None)
                kanban_zone_api._load_env_file()
                self.assertEqual(os.environ.get("KZ_TEST_TOKEN"), "abc123")
            finally:
                os.chdir(orig_cwd)
                kanban_zone_api.REAL_HERE = orig_real
                if not had_before:
                    os.environ.pop("KZ_TEST_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
