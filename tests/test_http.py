import base64
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import http as kanban_zone_http


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
        kanban_zone_http._cached_auth_header = None
        os.environ["KANBAN_ZONE_API_KEY"] = "abc:secret"
        self._orig_base = kanban_zone_http.BASE_URL
        kanban_zone_http.BASE_URL = self.base

    def tearDown(self):
        kanban_zone_http.BASE_URL = self._orig_base
        os.environ.pop("KANBAN_ZONE_API_KEY", None)
        kanban_zone_http._cached_auth_header = None

    def test_get_returns_parsed_json(self):
        result = kanban_zone_http.api_request("GET", "/anything")
        self.assertEqual(result, {"ok": True})

    def test_authorization_header_is_basic_base64(self):
        kanban_zone_http.api_request("GET", "/x")
        expected = "Basic " + base64.b64encode(b"abc:secret").decode()
        self.assertEqual(_Handler.last_request["headers"]["Authorization"], expected)

    def test_user_agent_header_is_set(self):
        kanban_zone_http.api_request("GET", "/x")
        self.assertEqual(
            _Handler.last_request["headers"]["User-Agent"],
            f"kanban-zone-skill/{kanban_zone_http.SKILL_VERSION}",
        )

    def test_query_params_appended(self):
        kanban_zone_http.api_request("GET", "/x", params={"a": "1", "b": "two"})
        self.assertIn("a=1", _Handler.last_request["path"])
        self.assertIn("b=two", _Handler.last_request["path"])

    def test_post_body_serialised_as_json(self):
        kanban_zone_http.api_request("POST", "/x", body={"hello": "world"})
        self.assertEqual(json.loads(_Handler.last_request["body"]), {"hello": "world"})
        self.assertEqual(
            _Handler.last_request["headers"]["Content-Type"], "application/json"
        )

    def test_204_returns_none(self):
        result = kanban_zone_http.api_request("PATCH", "/x", body={})
        self.assertIsNone(result)

    def test_non_2xx_raises_kzapierror_with_status_and_body(self):
        with self.assertRaises(kanban_zone_http.KanbanZoneApiError) as cm:
            kanban_zone_http.api_request("GET", "/error/foo")
        self.assertEqual(cm.exception.status, 404)
        self.assertIn("not found", cm.exception.body)

    def test_missing_api_key_raises(self):
        os.environ.pop("KANBAN_ZONE_API_KEY", None)
        kanban_zone_http._cached_auth_header = None
        with self.assertRaises(kanban_zone_http.KanbanZoneAuthError):
            kanban_zone_http.api_request("GET", "/x")

    def test_cached_auth_header_reused(self):
        """Calling api_request twice should reuse the cached auth header (line 33 branch)."""
        kanban_zone_http.api_request("GET", "/x")
        first = kanban_zone_http._cached_auth_header
        kanban_zone_http.api_request("GET", "/x")
        self.assertEqual(kanban_zone_http._cached_auth_header, first)

    def test_set_api_token_overrides_env(self):
        """set_api_token bypasses env var and caches the supplied token (line 49)."""
        kanban_zone_http.set_api_token("override:token")
        kanban_zone_http.api_request("GET", "/x")
        import base64 as _b64
        expected = "Basic " + _b64.b64encode(b"override:token").decode()
        self.assertEqual(_Handler.last_request["headers"]["Authorization"], expected)

    def test_params_with_none_values_omitted(self):
        """None values in params dict are dropped before building the query string (line 64)."""
        kanban_zone_http.api_request("GET", "/x", params={"present": "yes", "absent": None})
        self.assertIn("present=yes", _Handler.last_request["path"])
        self.assertNotIn("absent", _Handler.last_request["path"])

    def test_url_error_raises_kzapierror(self):
        """urllib.error.URLError (e.g. network down) is wrapped in KanbanZoneApiError (lines 86-87)."""
        import urllib.error
        from unittest.mock import patch as _patch
        with _patch("urllib.request.urlopen",
                    side_effect=urllib.error.URLError("name or service not known")):
            with self.assertRaises(kanban_zone_http.KanbanZoneApiError) as cm:
                kanban_zone_http.api_request("GET", "/x")
        self.assertEqual(cm.exception.status, 0)
        self.assertIn("name or service", cm.exception.body)

    def test_non_json_response_raises_kzapierror(self):
        """If server returns non-JSON on a 2xx, KanbanZoneApiError is raised (lines 93-94)."""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading

        class _BrokenHandler(BaseHTTPRequestHandler):
            def log_message(self, *_a, **_kw):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header("content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"not json!")

        srv2 = HTTPServer(("127.0.0.1", 0), _BrokenHandler)
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        host, port = srv2.server_address
        orig = kanban_zone_http.BASE_URL
        kanban_zone_http.BASE_URL = f"http://{host}:{port}/v1"
        try:
            with self.assertRaises(kanban_zone_http.KanbanZoneApiError) as cm:
                kanban_zone_http.api_request("GET", "/x")
            self.assertIn("non-JSON", cm.exception.body)
        finally:
            kanban_zone_http.BASE_URL = orig
            srv2.shutdown()


if __name__ == "__main__":
    unittest.main()
