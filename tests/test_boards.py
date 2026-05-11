import io
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import boards as kz_boards
from tests.fakes import FakeApi


def _fixture(name):
    path = os.path.join("tests", "fixtures", name)
    with open(path) as f:
        return json.load(f)


class _Ctx:
    pretty = False
    board = "BOARD1"
    cache = None


def _ns(**kw):
    return type("N", (), kw)()


class TestBoards(unittest.TestCase):
    def test_list_default(self):
        buf = io.StringIO()
        with FakeApi() as fake, patch("sys.stdout", buf):
            fake.expect("GET", "/boards", params={"includeArchived": False, "includeColumns": False}).returns(_fixture("boards_list.json"))
            kz_boards.cmd_list(_ns(include_archived=False, include_columns=False), _Ctx())
        self.assertIn('"BOARD1"', buf.getvalue())

    def test_list_with_archived(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards", params={"includeArchived": True, "includeColumns": False}).returns({"count": 0, "boards": []})
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_list(_ns(include_archived=True, include_columns=False), _Ctx())

    def test_get_uses_publicId_and_includes(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1", params={
                "includeColumns": True, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({"publicId": "BOARD1", "name": "Roadmap"})
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_get(_ns(
                    include_columns=True, include_members=False,
                    include_labels=False, include_custom_fields=False,
                ), _Ctx())

    def test_columns(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/columns").returns([{"_id": "c1", "title": "Backlog"}])
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_columns(_ns(), _Ctx())

    def test_labels(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/labels").returns([{"name": "Bug"}])
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_labels(_ns(), _Ctx())

    def test_members(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/members").returns([{"email": "a@b.com"}])
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_members(_ns(), _Ctx())

    def test_custom_fields(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/custom-fields").returns([{"label": "Sprint"}])
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_custom_fields(_ns(), _Ctx())

    def test_templates(self):
        with FakeApi() as fake:
            fake.expect("GET", "/templates/BOARD1").returns([{"publicId": "TPL1"}])
            with patch("sys.stdout", io.StringIO()):
                kz_boards.cmd_templates(_ns(), _Ctx())

    def test_get_requires_board(self):
        ctx = _Ctx()
        ctx.board = None
        with self.assertRaises(ValueError):
            kz_boards.cmd_get(_ns(
                include_columns=False, include_members=False,
                include_labels=False, include_custom_fields=False,
            ), ctx)


if __name__ == "__main__":
    unittest.main()
