import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import reports as kanban_zone_reports
from tests.fakes import FakeApi


class _Ctx:
    pretty = False
    board = "BOARD1"
    cache = None


def _ns(**kw):
    return type("N", (), kw)()


REPORT_TYPES = [
    ("throughput", "cmd_throughput"),
    ("arrival-rate", "cmd_arrival_rate"),
    ("cycle-time", "cmd_cycle_time"),
    ("lead-time", "cmd_lead_time"),
    ("flow", "cmd_flow"),
    ("flow-efficiency", "cmd_flow_efficiency"),
    ("allocation", "cmd_allocation"),
    ("abandoned-effort", "cmd_abandoned_effort"),
]


class TestReports(unittest.TestCase):
    def test_each_report_uses_correct_path(self):
        for slug, fn_name in REPORT_TYPES:
            with self.subTest(report=slug):
                with FakeApi() as fake:
                    fake.expect("GET", f"/boards/BOARD1/reports/{slug}",
                                params={"from": "2026-01-01", "to": "2026-04-01"}
                                ).returns({"data": []})
                    handler = getattr(kanban_zone_reports, fn_name)
                    with patch("sys.stdout", io.StringIO()):
                        handler(_ns(from_date="2026-01-01", to_date="2026-04-01"), _Ctx())

    def test_missing_dates_omits_params(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/reports/throughput", params=None
                        ).returns({"data": []})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_reports.cmd_throughput(_ns(from_date=None, to_date=None), _Ctx())

    def test_from_date_only(self):
        """_run_report with only from_date set (line 10-11, 14 branch)."""
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/reports/throughput",
                        params={"from": "2026-01-01"}).returns({"data": []})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_reports.cmd_throughput(_ns(from_date="2026-01-01", to_date=None), _Ctx())

    def test_to_date_only(self):
        """_run_report with only to_date set (line 10, 12-13 branch)."""
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/reports/throughput",
                        params={"to": "2026-04-01"}).returns({"data": []})
            with patch("sys.stdout", io.StringIO()):
                kanban_zone_reports.cmd_throughput(_ns(from_date=None, to_date="2026-04-01"), _Ctx())

    def test_no_board_raises(self):
        """_run_report raises ValueError when board is missing (line 8)."""
        ctx = _Ctx()
        ctx.board = None
        with self.assertRaises(ValueError):
            kanban_zone_reports.cmd_throughput(_ns(from_date=None, to_date=None), ctx)

    def test_all_report_types_no_dates(self):
        """Exercise every _cmd_* one-liner via subTest for the no-dates path."""
        handlers = [
            kanban_zone_reports.cmd_arrival_rate,
            kanban_zone_reports.cmd_cycle_time,
            kanban_zone_reports.cmd_lead_time,
            kanban_zone_reports.cmd_flow,
            kanban_zone_reports.cmd_flow_efficiency,
            kanban_zone_reports.cmd_allocation,
            kanban_zone_reports.cmd_abandoned_effort,
        ]
        slugs = [
            "arrival-rate", "cycle-time", "lead-time",
            "flow", "flow-efficiency", "allocation", "abandoned-effort",
        ]
        for handler, slug in zip(handlers, slugs):
            with self.subTest(slug=slug):
                with FakeApi() as fake:
                    fake.expect("GET", f"/boards/BOARD1/reports/{slug}",
                                params=None).returns({"data": []})
                    with patch("sys.stdout", io.StringIO()):
                        handler(_ns(from_date=None, to_date=None), _Ctx())


if __name__ == "__main__":
    unittest.main()
