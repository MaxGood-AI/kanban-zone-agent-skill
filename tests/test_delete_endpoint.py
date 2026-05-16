"""Regression tests for Kanban Zone's broken DELETE endpoints.

Kanban Zone's DELETE endpoints are non-functional server-side: their AWS edge
strips the request body, the routes then reject the empty body with
``HTTP 200`` + ``{"message": "Body Parser failed ..."}``, and nothing is
deleted. (Confirmed live 2026-05-16; reported to Kanban Zone.)

The skill cannot make delete work — that needs a Kanban Zone server-side fix —
but it must never report a fake success. Every delete command routes its
request through ``http.delete_resource()``, which raises
``KanbanZoneDeleteUnsupportedError`` (carrying an actionable, human- and
agent-readable message) instead of printing ``{"deleted": true}``.

These tests guard: (1) each delete command sends ``body={}``; (2) a genuine
204 success is still reported; (3) the body-parser failure surfaces as a
``KanbanZoneDeleteUnsupportedError`` with a helpful message; (4) that error
is catchable by the CLI's top-level handler.
"""
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kanban_zone import cards as kanban_zone_cards
from kanban_zone import checklists as kanban_zone_chk
from kanban_zone import http as kanban_zone_http
from kanban_zone import tasks as kanban_zone_tasks
from kanban_zone import tokens as kanban_zone_tokens
from kanban_zone import webhooks as kanban_zone_webhooks
from kanban_zone.cache import Cache
from tests.fakes import FakeApi


CHK_ID = "abcd1234ef5678901234abcd"
TASK_ID = "ffff1111eeee2222dddd3333"
CARD_OID = "6700aabbccddeeff00112233"
WH_ID = "1111222233334444aaaabbbb"
TOKEN_ID = "ccccddddeeeeffff00001111"

# The exact 200-with-error payload Kanban Zone returns for a body it cannot parse.
BODY_PARSER_ERROR = {
    "message": "Body Parser failed to parse request --> Unexpected end of JSON input"
}


class _Ctx:
    """Minimal ctx — the simple delete commands only read ctx.pretty."""
    pretty = False


def _ns(**kw):
    return type("N", (), kw)()


def _run(func, ctx=None):
    """Run a cmd_* handler, returning whatever it wrote to stdout."""
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        func(ctx or _Ctx())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# http.delete_resource — the shared helper every delete command calls.
# ---------------------------------------------------------------------------
class TestDeleteResourceHelper(unittest.TestCase):
    def test_sends_empty_json_body(self):
        with FakeApi() as fake:
            fake.expect("DELETE", "/tasks/x").returns(None)
            kanban_zone_http.delete_resource("task", "/tasks/x")
        self.assertEqual(fake.calls[0].method, "DELETE")
        self.assertEqual(fake.calls[0].body, {})

    def test_returns_none_on_real_success(self):
        with FakeApi() as fake:
            fake.expect("DELETE", "/tasks/x").returns(None)
            self.assertIsNone(kanban_zone_http.delete_resource("task", "/tasks/x"))

    def test_returns_resource_object_untouched(self):
        """A genuine resource object (carries _id) is passed straight back."""
        obj = {"_id": TASK_ID, "message": "anything"}
        with FakeApi() as fake:
            fake.expect("DELETE", "/tasks/x").returns(obj)
            self.assertEqual(kanban_zone_http.delete_resource("task", "/tasks/x"), obj)

    def test_body_parser_error_raises_delete_unsupported(self):
        with FakeApi() as fake:
            fake.expect("DELETE", "/tasks/x").returns(BODY_PARSER_ERROR)
            with self.assertRaises(kanban_zone_http.KanbanZoneDeleteUnsupportedError):
                kanban_zone_http.delete_resource("task", "/tasks/x")

    def test_other_error_envelope_is_plain_api_error(self):
        """A non-body-parser 200 envelope surfaces as a plain API error, not
        the delete-unsupported subclass."""
        with FakeApi() as fake:
            fake.expect("DELETE", "/tasks/x").returns({"message": "Not found"})
            with self.assertRaises(kanban_zone_http.KanbanZoneApiError) as cm:
                kanban_zone_http.delete_resource("task", "/tasks/x")
        self.assertNotIsInstance(
            cm.exception, kanban_zone_http.KanbanZoneDeleteUnsupportedError)

    def test_passes_params_through(self):
        with FakeApi() as fake:
            fake.expect("DELETE", "/cards/x",
                        params={"board": "B1"}).returns(None)
            kanban_zone_http.delete_resource("card", "/cards/x",
                                             params={"board": "B1"})
        self.assertEqual(fake.calls[0].params, {"board": "B1"})


# ---------------------------------------------------------------------------
# The error must be helpful (to humans and agents) and catchable by the CLI.
# ---------------------------------------------------------------------------
class TestDeleteErrorIsHelpfulAndCatchable(unittest.TestCase):
    def _raise(self, resource="checklist"):
        with FakeApi() as fake:
            fake.expect("DELETE", "/x").returns(BODY_PARSER_ERROR)
            try:
                kanban_zone_http.delete_resource(resource, "/x")
            except kanban_zone_http.KanbanZoneDeleteUnsupportedError as exc:
                return exc
        self.fail("expected KanbanZoneDeleteUnsupportedError")

    def test_message_names_the_resource(self):
        self.assertIn("checklist", str(self._raise("checklist")))
        self.assertIn("webhook", str(self._raise("webhook")))

    def test_message_states_it_was_not_deleted(self):
        self.assertIn("NOT deleted", str(self._raise()))

    def test_message_points_to_the_web_ui_workaround(self):
        self.assertIn("web UI", str(self._raise()))

    def test_message_says_it_is_a_kanbanzone_bug_and_retrying_is_futile(self):
        msg = str(self._raise())
        self.assertIn("Kanban Zone", msg)
        self.assertIn("retrying will not help", msg)

    def test_is_catchable_as_kanbanzone_api_error(self):
        """main() catches KanbanZoneApiError — the subclass must be caught too."""
        exc = self._raise()
        self.assertIsInstance(exc, kanban_zone_http.KanbanZoneApiError)

    def test_status_is_none_so_error_envelope_stays_clean(self):
        """status=None keeps a misleading '200' out of the CLI error output."""
        self.assertIsNone(self._raise().status)


# ---------------------------------------------------------------------------
# Every delete command — checklists, tasks, webhooks, tokens, cards.
# ---------------------------------------------------------------------------
class TestDeleteCommands(unittest.TestCase):
    """All five delete commands send body={} and surface Kanban Zone's
    body-parser failure as KanbanZoneDeleteUnsupportedError."""

    def _cards_ctx(self):
        ctx = _Ctx()
        ctx.board = "BOARD1"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ctx.cache = Cache(os.path.join(tmp.name, "c.json"))
        return ctx

    def _cases(self):
        # (label, path, params, ctx_factory, run(ctx))
        return [
            ("checklist", f"/checklists/{CHK_ID}", None, _Ctx,
             lambda ctx: kanban_zone_chk.cmd_delete(_ns(id=CHK_ID), ctx)),
            ("task", f"/tasks/{TASK_ID}", None, _Ctx,
             lambda ctx: kanban_zone_tasks.cmd_delete(_ns(id=TASK_ID), ctx)),
            ("webhook", f"/webhooks/{WH_ID}", None, _Ctx,
             lambda ctx: kanban_zone_webhooks.cmd_delete(_ns(id=WH_ID), ctx)),
            ("token", f"/tokens/{TOKEN_ID}", None, _Ctx,
             lambda ctx: kanban_zone_tokens.cmd_revoke(_ns(id=TOKEN_ID), ctx)),
            ("card", f"/cards/{CARD_OID}", {"board": "BOARD1"}, self._cards_ctx,
             lambda ctx: kanban_zone_cards.cmd_delete(_ns(id=CARD_OID), ctx)),
        ]

    def test_all_commands_send_empty_json_body(self):
        for label, path, params, ctx_factory, run in self._cases():
            with self.subTest(command=label):
                with FakeApi() as fake:
                    fake.expect("DELETE", path, params=params).returns(None)
                    _run(run, ctx_factory())
                self.assertEqual(fake.calls[0].body, {})

    def test_all_commands_report_real_success(self):
        for label, path, params, ctx_factory, run in self._cases():
            with self.subTest(command=label):
                with FakeApi() as fake:
                    fake.expect("DELETE", path, params=params).returns(None)
                    out = _run(run, ctx_factory())
                self.assertTrue(json.loads(out).get("id"))

    def test_all_commands_raise_on_body_parser_error(self):
        for label, path, params, ctx_factory, run in self._cases():
            with self.subTest(command=label):
                with FakeApi() as fake:
                    fake.expect("DELETE", path,
                                params=params).returns(BODY_PARSER_ERROR)
                    with self.assertRaises(
                            kanban_zone_http.KanbanZoneDeleteUnsupportedError):
                        _run(run, ctx_factory())


# ---------------------------------------------------------------------------
# End-to-end — cmd_delete driven through the real http stack against a local
# server that reproduces Kanban Zone's behaviour.
# ---------------------------------------------------------------------------
class _KZHandler(BaseHTTPRequestHandler):
    """Stand-in Kanban Zone DELETE endpoint.

    mode == "accept": a DELETE carrying a parseable body 204s (success).
    mode == "reject": every DELETE trips the body parser — models the live
                      bug, where the body never reaches the route.
    """
    last_request = {}
    mode = "accept"

    def log_message(self, *_a, **_kw):
        pass

    def do_DELETE(self):
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b""
        _KZHandler.last_request = {"method": self.command, "path": self.path}
        if _KZHandler.mode == "accept" and raw:
            self.send_response(204)
            self.end_headers()
            return
        payload = json.dumps(BODY_PARSER_ERROR).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class TestDeleteEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _KZHandler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        host, port = cls.srv.server_address
        cls.base = f"http://{host}:{port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        kanban_zone_http._cached_auth_header = None
        os.environ["KANBAN_ZONE_API_KEY"] = "abc:secret"
        self._orig_base = kanban_zone_http.BASE_URL
        kanban_zone_http.BASE_URL = self.base
        _KZHandler.mode = "accept"

    def tearDown(self):
        kanban_zone_http.BASE_URL = self._orig_base
        os.environ.pop("KANBAN_ZONE_API_KEY", None)
        kanban_zone_http._cached_auth_header = None

    def test_delete_succeeds_when_api_accepts_body(self):
        """If Kanban Zone accepts a body-bearing DELETE, the CLI reports a
        real success."""
        out = _run(lambda ctx: kanban_zone_chk.cmd_delete(_ns(id=CHK_ID), ctx))
        self.assertEqual(json.loads(out), {"deleted": True, "id": CHK_ID})

    def test_delete_surfaces_helpful_error_when_api_rejects(self):
        """The live case: Kanban Zone rejects the DELETE — the CLI raises a
        KanbanZoneDeleteUnsupportedError with the actionable message."""
        _KZHandler.mode = "reject"
        with self.assertRaises(
                kanban_zone_http.KanbanZoneDeleteUnsupportedError) as cm:
            _run(lambda ctx: kanban_zone_tasks.cmd_delete(_ns(id=TASK_ID), ctx))
        msg = str(cm.exception)
        self.assertIn("task", msg)
        self.assertIn("NOT deleted", msg)
        self.assertIn("web UI", msg)


if __name__ == "__main__":
    unittest.main()
