import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import tasks as kanban_zone_tasks
from tests.fakes import FakeApi


CHK_ID = "abcd1234ef5678901234abcd"
TASK_ID = "ffff1111eeee2222dddd3333"
DEST_CHK = "1111aaaa2222bbbb3333cccc"


class _Ctx:
    pretty = False
    board = "BOARD1"
    cache = None


def _ns(**kw):
    return type("N", (), kw)()


class TestTasks(unittest.TestCase):
    def test_create_minimal(self):
        with FakeApi() as fake:
            fake.expect("POST", "/tasks", body={
                "checklist": CHK_ID, "description": "Pick up groceries",
            }).returns({"_id": TASK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_create(_ns(
                    checklist=CHK_ID, description="Pick up groceries",
                    position=None, due_at=None,
                ), _Ctx())

    def test_create_with_position_and_due(self):
        with FakeApi() as fake:
            fake.expect("POST", "/tasks", body={
                "checklist": CHK_ID, "description": "X",
                "position": 0, "dueAt": "2026-06-01T17:00:00.000Z",
            }).returns({"_id": TASK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_create(_ns(
                    checklist=CHK_ID, description="X",
                    position=0, due_at="2026-06-01T17:00:00.000Z",
                ), _Ctx())

    def test_update_completed(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/tasks/{TASK_ID}", body={
                "completed": True,
            }).returns({"_id": TASK_ID, "completed": True})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_update(_ns(
                    id=TASK_ID, completed=True, description=None,
                    position=None, due_at=None,
                ), _Ctx())

    def test_delete(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/tasks/{TASK_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_delete(_ns(id=TASK_ID), _Ctx())

    def test_move_between_checklists(self):
        with FakeApi() as fake:
            fake.expect("POST", f"/tasks/{TASK_ID}/move", body={
                "checklistFrom": CHK_ID,
                "checklistTo": DEST_CHK,
                "position": 0,
            }).returns({"_id": TASK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_move(_ns(
                    id=TASK_ID, checklist_from=CHK_ID,
                    checklist_to=DEST_CHK, position=0,
                ), _Ctx())

    def test_update_all_fields(self):
        """cmd_update with all four fields populated (lines 21-27 branches)."""
        with FakeApi() as fake:
            fake.expect("PATCH", f"/tasks/{TASK_ID}", body={
                "completed": False,
                "description": "Updated text",
                "position": 2,
                "dueAt": "2026-12-31",
            }).returns({"_id": TASK_ID})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_tasks.cmd_update(_ns(
                    id=TASK_ID, completed=False, description="Updated text",
                    position=2, due_at="2026-12-31",
                ), _Ctx())

    def test_update_no_fields_raises(self):
        """cmd_update with no fields set raises ValueError (line 27 guard)."""
        with self.assertRaises(ValueError):
            kanban_zone_tasks.cmd_update(_ns(
                id=TASK_ID, completed=None, description=None,
                position=None, due_at=None,
            ), _Ctx())


if __name__ == "__main__":
    unittest.main()
