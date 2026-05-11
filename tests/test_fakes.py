import sys
import unittest

sys.path.insert(0, "scripts")
from kz import http as kz_http
from tests.fakes import FakeApi


class TestFakeApi(unittest.TestCase):
    def test_returns_queued_response(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards").returns({"count": 0, "boards": []})
            self.assertEqual(kz_http.api_request("GET", "/boards"), {"count": 0, "boards": []})
            fake.assert_no_more_calls()

    def test_records_actual_call_args(self):
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={"title": "x"}).returns({"ok": True})
            kz_http.api_request("POST", "/cards", body={"title": "x"})
            call = fake.calls[0]
            self.assertEqual(call.method, "POST")
            self.assertEqual(call.path, "/cards")
            self.assertEqual(call.body, {"title": "x"})

    def test_unexpected_call_raises(self):
        with self.assertRaises(AssertionError):
            with FakeApi() as fake:
                kz_http.api_request("GET", "/whatever")

    def test_path_mismatch_raises(self):
        with self.assertRaises(AssertionError):
            with FakeApi() as fake:
                fake.expect("GET", "/boards").returns({})
                kz_http.api_request("GET", "/cards")

    def test_assert_no_more_calls_fails_when_queue_not_drained(self):
        with self.assertRaises(AssertionError):
            with FakeApi() as fake:
                fake.expect("GET", "/x").returns({})
                fake.expect("GET", "/y").returns({})
                kz_http.api_request("GET", "/x")
                fake.assert_no_more_calls()


if __name__ == "__main__":
    unittest.main()
