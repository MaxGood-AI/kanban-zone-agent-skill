import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import reports as kz_reports
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
                    handler = getattr(kz_reports, fn_name)
                    with patch("sys.stdout", io.StringIO()):
                        handler(_ns(from_date="2026-01-01", to_date="2026-04-01"), _Ctx())

    def test_missing_dates_omits_params(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1/reports/throughput", params=None
                        ).returns({"data": []})
            with patch("sys.stdout", io.StringIO()):
                kz_reports.cmd_throughput(_ns(from_date=None, to_date=None), _Ctx())


if __name__ == "__main__":
    unittest.main()
