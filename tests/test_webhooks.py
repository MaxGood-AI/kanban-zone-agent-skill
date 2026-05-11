import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import webhooks as kz_webhooks
from tests.fakes import FakeApi


HOOK_ID = "11112222333344445555aaaa"


class _Ctx:
    pretty = False
    board = "BOARD1"
    cache = None


def _ns(**kw):
    return type("N", (), kw)()


class TestWebhooksCRUD(unittest.TestCase):
    def test_list(self):
        with FakeApi() as fake:
            fake.expect("GET", "/webhooks").returns([{"_id": HOOK_ID}])
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_list(_ns(), _Ctx())

    def test_get(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/webhooks/{HOOK_ID}").returns({"_id": HOOK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_get(_ns(id=HOOK_ID), _Ctx())

    def test_create(self):
        with FakeApi() as fake:
            fake.expect("POST", "/webhooks", body={
                "board": "BOARD1", "event": "CARD_CREATED",
                "url": "https://h.example/webhook",
            }).returns({"_id": HOOK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_create(_ns(
                    event="CARD_CREATED", url="https://h.example/webhook",
                ), _Ctx())

    def test_update(self):
        with FakeApi() as fake:
            fake.expect("PUT", f"/webhooks/{HOOK_ID}", body={
                "url": "https://h.example/v2",
            }).returns({"_id": HOOK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_update(_ns(
                    id=HOOK_ID, url="https://h.example/v2", event=None,
                ), _Ctx())

    def test_delete(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/webhooks/{HOOK_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_delete(_ns(id=HOOK_ID), _Ctx())

    def test_test(self):
        with FakeApi() as fake:
            fake.expect("POST", f"/webhooks/{HOOK_ID}/test").returns({"sent": True})
            with patch("sys.stdout", io.StringIO()):
                kz_webhooks.cmd_test(_ns(id=HOOK_ID), _Ctx())


class TestVerifySignature(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.payload_path = os.path.join(self._tmp.name, "payload.json")
        self.payload = json.dumps({"CardItem": {"number": 42}}).encode()
        with open(self.payload_path, "wb") as f:
            f.write(self.payload)
        self.key = "secret-key"
        self.good = hmac.new(self.key.encode(), self.payload, hashlib.sha1).hexdigest()

    def tearDown(self):
        self._tmp.cleanup()

    def test_match_returns_exit_zero(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = kz_webhooks.cmd_verify_signature(_ns(
                webhook_key=self.key, payload_file=self.payload_path,
                signature=self.good,
            ), _Ctx())
        out = json.loads(buf.getvalue())
        self.assertTrue(out["verified"])
        self.assertEqual(out["computed"], self.good)
        self.assertEqual(rc, 0)

    def test_mismatch_exits_one(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = kz_webhooks.cmd_verify_signature(_ns(
                webhook_key=self.key, payload_file=self.payload_path,
                signature="0" * 40,
            ), _Ctx())
        out = json.loads(buf.getvalue())
        self.assertFalse(out["verified"])
        self.assertEqual(rc, 1)

    def test_key_from_env(self):
        os.environ["KZ_WEBHOOK_KEY"] = self.key
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = kz_webhooks.cmd_verify_signature(_ns(
                    webhook_key=None, payload_file=self.payload_path,
                    signature=self.good,
                ), _Ctx())
            self.assertEqual(rc, 0)
        finally:
            os.environ.pop("KZ_WEBHOOK_KEY")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            kz_webhooks.cmd_verify_signature(_ns(
                webhook_key=None, payload_file=self.payload_path,
                signature=self.good,
            ), _Ctx())


if __name__ == "__main__":
    unittest.main()
