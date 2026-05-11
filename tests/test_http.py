import base64
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import http as kz_http


class _Handler(BaseHTTPRequestHandler):
    last_request = {}

    def log_message(self, *_a, **_kw):
        pass

    def _record(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        _Handler.last_request = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers),
            "body": body.decode("utf-8") if body else "",
        }

    def do_GET(self):
        self._record()
        if self.path.startswith("/v1/error"):
            self.send_response(404)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "not found"}')
            return
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_POST(self):
        self._record()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"created": true}')

    def do_PATCH(self):
        self._record()
        self.send_response(204)
        self.end_headers()

    def do_DELETE(self):
        self._record()
        self.send_response(204)
        self.end_headers()

    def do_PUT(self):
        self.do_POST()


def _start_server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class TestApiRequest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _start_server()
        cls.host, cls.port = cls.srv.server_address
        cls.base = f"http://{cls.host}:{cls.port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        kz_http._cached_auth_header = None
        os.environ["KANBAN_ZONE_API_KEY"] = "abc:secret"
        self._orig_base = kz_http.BASE_URL
        kz_http.BASE_URL = self.base

    def tearDown(self):
        kz_http.BASE_URL = self._orig_base
        os.environ.pop("KANBAN_ZONE_API_KEY", None)
        kz_http._cached_auth_header = None

    def test_get_returns_parsed_json(self):
        result = kz_http.api_request("GET", "/anything")
        self.assertEqual(result, {"ok": True})

    def test_authorization_header_is_basic_base64(self):
        kz_http.api_request("GET", "/x")
        expected = "Basic " + base64.b64encode(b"abc:secret").decode()
        self.assertEqual(_Handler.last_request["headers"]["Authorization"], expected)

    def test_user_agent_header_is_set(self):
        kz_http.api_request("GET", "/x")
        self.assertEqual(
            _Handler.last_request["headers"]["User-Agent"],
            f"kanban-zone-skill/{kz_http.SKILL_VERSION}",
        )

    def test_query_params_appended(self):
        kz_http.api_request("GET", "/x", params={"a": "1", "b": "two"})
        self.assertIn("a=1", _Handler.last_request["path"])
        self.assertIn("b=two", _Handler.last_request["path"])

    def test_post_body_serialised_as_json(self):
        kz_http.api_request("POST", "/x", body={"hello": "world"})
        self.assertEqual(json.loads(_Handler.last_request["body"]), {"hello": "world"})
        self.assertEqual(
            _Handler.last_request["headers"]["Content-Type"], "application/json"
        )

    def test_204_returns_none(self):
        result = kz_http.api_request("PATCH", "/x", body={})
        self.assertIsNone(result)

    def test_non_2xx_raises_kzapierror_with_status_and_body(self):
        with self.assertRaises(kz_http.KZApiError) as cm:
            kz_http.api_request("GET", "/error/foo")
        self.assertEqual(cm.exception.status, 404)
        self.assertIn("not found", cm.exception.body)

    def test_missing_api_key_raises(self):
        os.environ.pop("KANBAN_ZONE_API_KEY", None)
        kz_http._cached_auth_header = None
        with self.assertRaises(kz_http.KZAuthError):
            kz_http.api_request("GET", "/x")


if __name__ == "__main__":
    unittest.main()
