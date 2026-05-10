# Kanban Zone Skill v3.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the Kanban Zone skill from v2.1.0 (wrapping API v1.3) to v3.0.0 (wrapping API v1.4.0), adding ~38 new endpoints, restructuring the CLI into resource groups with hidden back-compat aliases, splitting the script into a `scripts/kz/` package, and adding a stdlib `unittest` suite at ≥95 % coverage.

**Architecture:** Single CLI entry point dispatches to per-resource handler modules. All HTTP goes through one `kz.http.api_request` chokepoint (mockable in tests). A bidirectional cache maps card numbers ↔ ObjectIds and stores board/column metadata. Every resource module owns its own argparse subparser and handler functions. Tests use a `FakeApi` context manager that monkey-patches `kz.http.api_request` with a programmable response queue.

**Tech Stack:** Python 3 (stdlib only at runtime — `argparse`, `urllib.request`, `json`, `base64`, `hmac`, `hashlib`, `tempfile`). Dev-only deps: `coverage` (HTML + console reporting). No web framework, no database, no third-party HTTP client.

**Spec:** `docs/superpowers/specs/2026-05-10-kanban-zone-skill-v3-design.md`

**Repo invariants (do not change):** `LICENSE.txt`, `.clawhubignore`, `KANBAN_ZONE_API_KEY` / `KANBAN_ZONE_BOARD_ID` env var names, `kanbanzone-cache.json` filename and location semantics.

**Conventions used in every task:**
- Test-first: write the failing test, run it to confirm it fails, write minimal implementation, run again to confirm pass, commit.
- Commit messages follow the platform style (`## Problem` / `## Solution` / `## Verified`, KZ card link if applicable, `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`).
- All tests run from repo root: `python3 -m unittest discover tests -v`.
- Coverage runs: `coverage run -m unittest discover tests && coverage report -m`.
- Stdlib only — no `pip install` for runtime code.

---

## Phase 0 — Setup

### Task 1: Repo skeleton and dev tooling

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/fixtures/.gitkeep`
- Create: `Makefile`
- Create: `.coveragerc`
- Modify: `.gitignore`

- [ ] **Step 1: Create the empty test package directory.**

```bash
mkdir -p tests/fixtures
touch tests/__init__.py tests/fixtures/.gitkeep
```

- [ ] **Step 2: Create `.coveragerc`.**

```ini
[run]
source = scripts/kz
branch = True

[report]
show_missing = True
skip_covered = False
fail_under = 95
exclude_lines =
    pragma: no cover
    raise NotImplementedError
    if __name__ == .__main__.:
```

- [ ] **Step 3: Create `Makefile`.**

```makefile
.PHONY: test coverage coverage-html lint clean

test:
	python3 -m unittest discover tests -v

coverage:
	coverage run -m unittest discover tests
	coverage report -m

coverage-html:
	coverage run -m unittest discover tests
	coverage html
	@echo "Open htmlcov/index.html"

lint:
	python3 -m compileall -q scripts tests

clean:
	rm -rf .coverage htmlcov tests/__pycache__ scripts/__pycache__ scripts/kz/__pycache__
```

- [ ] **Step 4: Update `.gitignore`.** Append:

```
.coverage
htmlcov/
tests/__pycache__/
scripts/__pycache__/
scripts/kz/__pycache__/
```

- [ ] **Step 5: Verify `make lint` passes (compiles the empty tests/ — should be a no-op success).**

```bash
make lint
```
Expected: exit 0, no output.

- [ ] **Step 6: Commit.**

```bash
git add tests/ Makefile .coveragerc .gitignore
git commit -m "$(cat <<'EOF'
Add v3 test scaffolding (Makefile, .coveragerc, tests/)

## Problem
v3 needs a stdlib unittest suite with =>=95% coverage. The repo currently
has no tests, no coverage config, no make targets.

## Solution
Add empty tests/ package with fixtures/ subdirectory, .coveragerc enforcing
95% fail-under, and a Makefile exposing test/coverage/coverage-html/lint/clean.
.gitignore updated to drop coverage and pycache artifacts.

## Verified
- make lint succeeds (compiles empty tests/).
- make test succeeds with "Ran 0 tests" output.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Create the empty `kz/` package

**Files:**
- Create: `scripts/kz/__init__.py`

- [ ] **Step 1: Create empty package marker.**

```bash
touch scripts/kz/__init__.py
```

Contents (one line):

```python
"""Kanban Zone API skill — internal package."""
```

- [ ] **Step 2: Verify it imports.**

```bash
cd scripts && python3 -c "import kz" && cd ..
```
Expected: exit 0, no output.

- [ ] **Step 3: Commit.**

```bash
git add scripts/kz/__init__.py
git commit -m "$(cat <<'EOF'
Add empty kz/ package marker

## Problem
v3 splits the monolithic kanban_zone_api.py into a kz/ package. Need the
empty package marker to start adding modules.

## Solution
Single-line scripts/kz/__init__.py.

## Verified
python3 -c "import kz" from scripts/ succeeds.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 1 — Foundation

### Task 3: Output module (`kz.output`)

**Files:**
- Create: `scripts/kz/output.py`
- Create: `tests/test_output.py`

- [ ] **Step 1: Write failing tests `tests/test_output.py`.**

```python
import io
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import output


class TestPrintJson(unittest.TestCase):
    def test_compact_default(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json({"a": 1, "b": [2, 3]}, pretty=False)
        self.assertEqual(buf.getvalue().strip(), '{"a": 1, "b": [2, 3]}')

    def test_pretty(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json({"a": 1}, pretty=True)
        self.assertIn('  "a": 1', buf.getvalue())

    def test_none_prints_null(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            output.print_json(None, pretty=False)
        self.assertEqual(buf.getvalue().strip(), "null")


class TestErrorExit(unittest.TestCase):
    def test_writes_json_to_stderr_and_exits_1(self):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            with self.assertRaises(SystemExit) as cm:
                output.error_exit("boom", status=429)
        self.assertEqual(cm.exception.code, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload, {"error": True, "status": 429, "message": "boom"})

    def test_status_optional(self):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            with self.assertRaises(SystemExit):
                output.error_exit("boom")
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload, {"error": True, "message": "boom"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure ("No module named kz.output" or similar).**

```bash
python3 -m unittest tests.test_output -v
```
Expected: ImportError or ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/kz/output.py`.**

```python
"""JSON output helpers for the Kanban Zone CLI."""
import json
import sys


def print_json(data, pretty=False):
    """Print parsed JSON to stdout, compact by default."""
    if pretty:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=False))
    else:
        sys.stdout.write(json.dumps(data, separators=(", ", ": ")))
    sys.stdout.write("\n")


def error_exit(message, status=None):
    """Write a structured error envelope to stderr and exit 1."""
    payload = {"error": True}
    if status is not None:
        payload["status"] = status
    payload["message"] = message
    sys.stderr.write(json.dumps(payload) + "\n")
    raise SystemExit(1)
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_output -v
```
Expected: 5 tests, all PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/output.py tests/test_output.py
git commit -m "$(cat <<'EOF'
Add kz.output JSON + error-exit helpers

## Problem
Every kz handler needs a consistent way to emit JSON and surface errors.
Inlining json.dumps everywhere would scatter the format and make a
--pretty global flag awkward to thread through.

## Solution
kz/output.py exposes print_json(data, pretty) and error_exit(message,
status). All handlers will call these instead of touching sys.stdout/stderr
directly. Tests cover compact/pretty/null and error-with-status/no-status.

## Verified
python3 -m unittest tests.test_output passes (5 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: HTTP layer (`kz.http`) — error model and request helper

**Files:**
- Create: `scripts/kz/http.py`
- Create: `tests/test_http.py`

- [ ] **Step 1: Write failing tests `tests/test_http.py`.**

```python
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
```

- [ ] **Step 2: Run — expect failure (module not yet defined).**

```bash
python3 -m unittest tests.test_http -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/kz/http.py`.**

```python
"""HTTP layer for the Kanban Zone CLI.

Single chokepoint for every API call. Handlers do not import urllib directly;
they call api_request() so tests can monkey-patch one function.
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SKILL_VERSION = "3.0.0"
BASE_URL = "https://integrations.kanbanzone.io/v1"

_cached_auth_header = None


class KZApiError(Exception):
    def __init__(self, status, body, request_line):
        super().__init__(f"{request_line} -> HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body
        self.request_line = request_line


class KZAuthError(Exception):
    pass


def _auth_header():
    global _cached_auth_header
    if _cached_auth_header is not None:
        return _cached_auth_header
    raw = os.environ.get("KANBAN_ZONE_API_KEY") or ""
    raw = raw.strip()
    if not raw:
        raise KZAuthError(
            "KANBAN_ZONE_API_KEY is not set (and --api-token was not passed)"
        )
    encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    _cached_auth_header = "Basic " + encoded
    return _cached_auth_header


def set_api_token(raw_token):
    """Override the API key for one process (used by --api-token CLI flag)."""
    global _cached_auth_header
    _cached_auth_header = "Basic " + base64.b64encode(
        raw_token.encode("utf-8")
    ).decode("ascii")


def api_request(method, path, params=None, body=None):
    """Send an HTTP request to the Kanban Zone API and return parsed JSON.

    Returns None on 204. Raises KZApiError on non-2xx, KZAuthError on missing key.
    """
    if not path.startswith("/"):
        path = "/" + path
    url = BASE_URL.rstrip("/") + path
    if params:
        flat = {k: v for k, v in params.items() if v is not None}
        if flat:
            url += "?" + urllib.parse.urlencode(flat, doseq=True)

    headers = {
        "Authorization": _auth_header(),
        "User-Agent": f"kanban-zone-skill/{SKILL_VERSION}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    request_line = f"{method} {url}"
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() or b""
        raise KZApiError(exc.code, raw.decode("utf-8", errors="replace"), request_line)
    except urllib.error.URLError as exc:
        raise KZApiError(0, str(exc.reason), request_line)

    if status == 204 or not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise KZApiError(
            status, f"non-JSON response: {raw[:200]!r}", request_line
        ) from exc
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_http -v
```
Expected: 8 tests, all PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/http.py tests/test_http.py
git commit -m "$(cat <<'EOF'
Add kz.http API request layer + unit tests

## Problem
v3 needs a single mockable HTTP chokepoint. v2 does HTTP inline in the
monolithic script, which makes test isolation impossible.

## Solution
kz/http.py exposes api_request(method, path, params, body) returning parsed
JSON (or None on 204). Auth header is base64(KANBAN_ZONE_API_KEY) cached
in-process. KZApiError carries status/body/request line; KZAuthError fires
when the key is missing. set_api_token() lets the CLI --api-token flag
override the env. Tests run a real http.server on an ephemeral port to
exercise URL building, auth header, User-Agent, query params, JSON body
serialization, 204 handling, and HTTP error mapping.

## Verified
python3 -m unittest tests.test_http passes (8 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: FakeApi test fixture (`tests.fakes`)

**Files:**
- Create: `tests/fakes.py`
- Create: `tests/test_fakes.py`

The `FakeApi` is the mocking primitive every resource test depends on. Build it once, test it once, then every later resource test can use it without re-justifying the pattern.

- [ ] **Step 1: Write failing tests `tests/test_fakes.py`.**

```python
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
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_fakes -v
```
Expected: ImportError on `tests.fakes`.

- [ ] **Step 3: Implement `tests/fakes.py`.**

```python
"""Test fakes for the kz package — primarily the FakeApi context manager."""
import sys
from dataclasses import dataclass, field
from typing import Any, List, Optional

sys.path.insert(0, "scripts")
from kz import http as kz_http


@dataclass
class _Expectation:
    method: str
    path: str
    params: Optional[dict] = None
    body: Any = None
    response: Any = None


@dataclass
class _Call:
    method: str
    path: str
    params: Optional[dict]
    body: Any


class _ExpectationBuilder:
    def __init__(self, expectation: _Expectation):
        self._expectation = expectation

    def returns(self, response):
        self._expectation.response = response
        return self


class FakeApi:
    """Context manager that monkey-patches kz.http.api_request with a queue."""

    def __init__(self):
        self.expectations: List[_Expectation] = []
        self.calls: List[_Call] = []
        self._original = None

    def __enter__(self):
        self._original = kz_http.api_request
        kz_http.api_request = self._intercept
        return self

    def __exit__(self, exc_type, exc, tb):
        kz_http.api_request = self._original

    def expect(self, method, path, params=None, body=None):
        exp = _Expectation(method=method, path=path, params=params, body=body)
        self.expectations.append(exp)
        return _ExpectationBuilder(exp)

    def assert_no_more_calls(self):
        outstanding = self.expectations[len(self.calls):]
        assert not outstanding, f"Unconsumed expectations: {outstanding!r}"

    def _intercept(self, method, path, params=None, body=None):
        self.calls.append(_Call(method, path, params, body))
        idx = len(self.calls) - 1
        assert idx < len(self.expectations), (
            f"Unexpected call {method} {path}; no more expectations queued"
        )
        exp = self.expectations[idx]
        assert exp.method == method, (
            f"Call {idx}: expected method {exp.method}, got {method}"
        )
        assert exp.path == path, (
            f"Call {idx}: expected path {exp.path}, got {path}"
        )
        if exp.params is not None:
            assert exp.params == params, (
                f"Call {idx}: expected params {exp.params}, got {params}"
            )
        if exp.body is not None:
            assert exp.body == body, (
                f"Call {idx}: expected body {exp.body}, got {body}"
            )
        return exp.response
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_fakes -v
```
Expected: 5 tests, all PASS.

- [ ] **Step 5: Commit.**

```bash
git add tests/fakes.py tests/test_fakes.py
git commit -m "$(cat <<'EOF'
Add FakeApi test fixture

## Problem
Every resource handler test needs to mock kz.http.api_request. Writing
ad-hoc unittest.mock.patch in every test file would duplicate setup,
hide intent, and lose the ability to assert what was actually called.

## Solution
tests/fakes.py exposes FakeApi as a context manager. Tests queue
expectations with .expect(method, path, params, body).returns(response),
then assert exhaustion with .assert_no_more_calls(). The actual call
record is exposed via .calls for finer assertions. The fake monkey-patches
kz.http.api_request on enter and restores on exit.

## Verified
python3 -m unittest tests.test_fakes passes (5 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Cache module (`kz.cache`) — board/column + bidirectional ID

**Files:**
- Create: `scripts/kz/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests `tests/test_cache.py`.**

```python
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
from kz.cache import Cache


class TestCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "cache.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_missing_file_returns_empty(self):
        c = Cache(self.path)
        self.assertEqual(c.get_board("XYZ"), None)

    def test_set_then_get_board(self):
        c = Cache(self.path)
        c.set_board("XYZ", "My Board")
        self.assertEqual(c.get_board("XYZ"), {"name": "My Board"})

    def test_set_and_get_columns(self):
        c = Cache(self.path)
        c.set_columns("XYZ", {"col1": {"name": "Backlog", "state": "Backlog"}})
        self.assertEqual(c.get_column("XYZ", "col1"), {"name": "Backlog", "state": "Backlog"})

    def test_card_mapping_bidirectional(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        self.assertEqual(c.get_card_oid("XYZ", 42), "6700aabbccddeeff00112233")
        self.assertEqual(c.get_card_number("XYZ", "6700aabbccddeeff00112233"), 42)

    def test_invalidate_card_removes_both_directions(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        c.invalidate_card("XYZ", 42)
        self.assertIsNone(c.get_card_oid("XYZ", 42))
        self.assertIsNone(c.get_card_number("XYZ", "6700aabbccddeeff00112233"))

    def test_invalidate_card_by_oid(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 42, "6700aabbccddeeff00112233")
        c.invalidate_card("XYZ", "6700aabbccddeeff00112233")
        self.assertIsNone(c.get_card_oid("XYZ", 42))
        self.assertIsNone(c.get_card_number("XYZ", "6700aabbccddeeff00112233"))

    def test_flush_persists_to_disk_atomically(self):
        c = Cache(self.path)
        c.set_card_mapping("XYZ", 1, "a" * 24)
        c.flush()
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["boards"]["XYZ"]["cards"]["byNumber"]["1"], "a" * 24)

    def test_load_v2_format_without_cards_block(self):
        # v2 cache file lacking the cards block must still load
        with open(self.path, "w") as f:
            json.dump({
                "boards": {"XYZ": {"name": "Old Board", "columns": {}}},
                "updated": "2024-01-01T00:00:00Z",
            }, f)
        c = Cache(self.path)
        self.assertEqual(c.get_board("XYZ"), {"name": "Old Board"})
        self.assertIsNone(c.get_card_oid("XYZ", 1))

    def test_no_op_cache_disables_persistence(self):
        c = Cache(self.path, enabled=False)
        c.set_card_mapping("XYZ", 1, "a" * 24)
        c.flush()
        self.assertFalse(os.path.exists(self.path))
        # but in-memory still works for the lifetime of the object
        self.assertEqual(c.get_card_oid("XYZ", 1), "a" * 24)

    def test_updated_timestamp_set_on_flush(self):
        c = Cache(self.path)
        c.set_board("XYZ", "B")
        c.flush()
        with open(self.path) as f:
            data = json.load(f)
        self.assertIn("updated", data)
        self.assertTrue(data["updated"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_cache -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/kz/cache.py`.**

```python
"""Persistent agent-side cache for board/column metadata + card number<->ObjectId.

Schema:
{
  "boards": {
    "<board-public-id>": {
      "name": "...",
      "columns": { "<col-id>": { "name": "...", "state": "..." } },
      "cards": {
        "byNumber":   { "42":   "<oid>" },
        "byObjectId": { "<oid>": 42 }
      }
    }
  },
  "updated": "ISO-8601"
}
"""
import datetime as _dt
import json
import os
import tempfile


class Cache:
    def __init__(self, path, enabled=True):
        self.path = path
        self.enabled = enabled
        self._data = {"boards": {}, "updated": None}
        if self.enabled and os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and "boards" in loaded:
                    self._data = loaded
            except (OSError, json.JSONDecodeError):
                pass

    def _board(self, public_id, create=False):
        boards = self._data.setdefault("boards", {})
        if public_id not in boards:
            if not create:
                return None
            boards[public_id] = {"name": None, "columns": {}, "cards": {"byNumber": {}, "byObjectId": {}}}
        b = boards[public_id]
        b.setdefault("columns", {})
        b.setdefault("cards", {"byNumber": {}, "byObjectId": {}})
        b["cards"].setdefault("byNumber", {})
        b["cards"].setdefault("byObjectId", {})
        return b

    def get_board(self, public_id):
        b = self._board(public_id, create=False)
        if b is None:
            return None
        return {"name": b.get("name")}

    def set_board(self, public_id, name):
        b = self._board(public_id, create=True)
        b["name"] = name

    def get_column(self, public_id, column_id):
        b = self._board(public_id, create=False)
        if not b:
            return None
        return b["columns"].get(column_id)

    def set_columns(self, public_id, columns):
        b = self._board(public_id, create=True)
        b["columns"] = dict(columns)

    def get_card_oid(self, public_id, number):
        b = self._board(public_id, create=False)
        if not b:
            return None
        return b["cards"]["byNumber"].get(str(number))

    def get_card_number(self, public_id, object_id):
        b = self._board(public_id, create=False)
        if not b:
            return None
        return b["cards"]["byObjectId"].get(object_id)

    def set_card_mapping(self, public_id, number, object_id):
        b = self._board(public_id, create=True)
        b["cards"]["byNumber"][str(number)] = object_id
        b["cards"]["byObjectId"][object_id] = int(number)

    def invalidate_card(self, public_id, number_or_oid):
        b = self._board(public_id, create=False)
        if not b:
            return
        s = str(number_or_oid)
        oid = b["cards"]["byNumber"].pop(s, None)
        if oid is not None:
            b["cards"]["byObjectId"].pop(oid, None)
            return
        number = b["cards"]["byObjectId"].pop(s, None)
        if number is not None:
            b["cards"]["byNumber"].pop(str(number), None)

    def flush(self):
        if not self.enabled:
            return
        self._data["updated"] = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".cache-", dir=os.path.dirname(self.path) or ".")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            finally:
                raise
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_cache -v
```
Expected: 10 tests, all PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/cache.py tests/test_cache.py
git commit -m "$(cat <<'EOF'
Add kz.cache with bidirectional card-id mapping

## Problem
v3 introduces card-number <-> ObjectId resolution (auto-detect ID kind).
The agent cache must store both directions so resolved ObjectIds can be
reused without re-paging /cards. v2's cache only stored boards/columns.

## Solution
kz/cache.py adds a Cache class with byNumber/byObjectId dicts under each
board entry. set_card_mapping writes both directions; invalidate_card
removes both regardless of which key the caller has. Atomic write via
tempfile + os.replace. Forward-compatible: v2 cache files (no cards block)
load cleanly. enabled=False short-circuits persistence for --no-cache.

## Verified
python3 -m unittest tests.test_cache passes (10 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: ID resolver (`kz.ids`)

**Files:**
- Create: `scripts/kz/ids.py`
- Create: `tests/test_ids.py`

- [ ] **Step 1: Write failing tests `tests/test_ids.py`.**

```python
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "scripts")
from kz import ids
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class TestDetectIdKind(unittest.TestCase):
    def test_pure_digits_is_number(self):
        self.assertEqual(ids.detect_id_kind("42"), "number")

    def test_24_hex_is_object_id(self):
        self.assertEqual(ids.detect_id_kind(CARD_OID), "object_id")

    def test_24_hex_uppercase_is_object_id(self):
        self.assertEqual(ids.detect_id_kind(CARD_OID.upper()), "object_id")

    def test_short_hex_raises(self):
        with self.assertRaises(ids.KZIdError):
            ids.detect_id_kind("abc123")

    def test_empty_raises(self):
        with self.assertRaises(ids.KZIdError):
            ids.detect_id_kind("")


class TestResolveCardObjectId(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_object_id_passthrough(self):
        with FakeApi() as fake:
            result = ids.resolve_card_object_id(CARD_OID, "BOARD1", self.cache)
            self.assertEqual(result, CARD_OID)
            fake.assert_no_more_calls()

    def test_number_with_cache_hit_returns_without_api_call(self):
        self.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            result = ids.resolve_card_object_id("42", "BOARD1", self.cache)
            self.assertEqual(result, CARD_OID)
            fake.assert_no_more_calls()

    def test_number_cache_miss_pages_until_match_then_caches(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 5, "hasMore": True,
                "cards": [
                    {"_id": "a" * 24, "number": 7, "title": "x"},
                    {"_id": "b" * 24, "number": 8, "title": "x"},
                ],
            })
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 2, "count": 100, "includeArchived": False,
            }).returns({
                "count": 3, "totalAvailable": 5, "hasMore": False,
                "cards": [
                    {"_id": "c" * 24, "number": 41, "title": "x"},
                    {"_id": CARD_OID, "number": 42, "title": "x"},
                    {"_id": "d" * 24, "number": 43, "title": "x"},
                ],
            })
            result = ids.resolve_card_object_id("42", "BOARD1", self.cache)
        self.assertEqual(result, CARD_OID)
        self.assertEqual(self.cache.get_card_oid("BOARD1", 42), CARD_OID)
        self.assertEqual(self.cache.get_card_number("BOARD1", CARD_OID), 42)

    def test_number_not_found_raises(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"count": 0, "totalAvailable": 0, "hasMore": False, "cards": []})
            with self.assertRaises(ids.KZIdError):
                ids.resolve_card_object_id("999", "BOARD1", self.cache)


class TestResolveCardNumber(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_number_passthrough(self):
        with FakeApi() as fake:
            self.assertEqual(ids.resolve_card_number("42", "B", self.cache), 42)
            fake.assert_no_more_calls()

    def test_object_id_cache_hit(self):
        self.cache.set_card_mapping("B", 42, CARD_OID)
        with FakeApi() as fake:
            self.assertEqual(ids.resolve_card_number(CARD_OID, "B", self.cache), 42)
            fake.assert_no_more_calls()

    def test_object_id_cache_miss_fetches_card(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns(
                {"_id": CARD_OID, "number": 42, "title": "x"}
            )
            self.assertEqual(ids.resolve_card_number(CARD_OID, "B", self.cache), 42)
            self.assertEqual(self.cache.get_card_oid("B", 42), CARD_OID)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_ids -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/kz/ids.py`.**

```python
"""Card identifier resolution.

Auto-detects card numbers (pure digits) vs ObjectIds (24-hex).
Resolves either direction through the agent cache, falling back to API calls.
"""
import re

from kz import http as kz_http

_NUMBER_RE = re.compile(r"^\d+$")
_OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")


class KZIdError(Exception):
    pass


def detect_id_kind(value):
    if not isinstance(value, str):
        value = str(value)
    if _NUMBER_RE.match(value):
        return "number"
    if _OBJECT_ID_RE.match(value):
        return "object_id"
    raise KZIdError(
        f"{value!r} is neither a card number (digits) nor a 24-hex ObjectId"
    )


def resolve_card_object_id(value, board, cache):
    """Return the ObjectId for a card identified by number or ObjectId."""
    kind = detect_id_kind(value)
    if kind == "object_id":
        return value
    number = int(value)
    cached = cache.get_card_oid(board, number)
    if cached is not None:
        return cached
    page = 1
    while True:
        resp = kz_http.api_request(
            "GET", "/cards",
            params={"board": board, "page": page, "count": 100, "includeArchived": False},
        )
        for card in (resp or {}).get("cards", []):
            cn = card.get("number")
            oid = card.get("_id")
            if cn is not None and oid:
                cache.set_card_mapping(board, cn, oid)
            if cn == number:
                return oid
        if not (resp or {}).get("hasMore"):
            break
        page += 1
    raise KZIdError(f"Card number {number} not found on board {board}")


def resolve_card_number(value, board, cache):
    """Return the card number for a card identified by number or ObjectId."""
    kind = detect_id_kind(value)
    if kind == "number":
        return int(value)
    cached = cache.get_card_number(board, value)
    if cached is not None:
        return cached
    resp = kz_http.api_request("GET", f"/cards/{value}")
    number = (resp or {}).get("number")
    if number is None:
        raise KZIdError(f"Card {value} returned no number field")
    cache.set_card_mapping(board, number, value)
    return int(number)
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_ids -v
```
Expected: 9 tests, all PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/ids.py tests/test_ids.py
git commit -m "$(cat <<'EOF'
Add kz.ids auto-detection + bidirectional resolver

## Problem
v3's CLI accepts a single --id flag for cards, auto-detecting whether the
user passed a card number or a 24-hex ObjectId. Most v1.4 endpoints use
ObjectId; the user-facing UX uses card numbers. We need a deterministic
resolver that consults the cache before paging /cards.

## Solution
detect_id_kind regex-matches digits/hex24. resolve_card_object_id pages
through /cards on cache miss, populating both directions of the cache as
it goes (so a single sweep warms the cache for every card on the board).
resolve_card_number does the reverse via GET /cards/{oid}.

## Verified
python3 -m unittest tests.test_ids passes (9 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: CLI entry skeleton (`scripts/kanban_zone_api.py`)

**Files:**
- Modify: `scripts/kanban_zone_api.py` (full rewrite — replaces v2 monolith)
- Create: `tests/test_cli_skeleton.py`

The new entry script keeps the `.env` loader from v2 and adds the global flags + group dispatch. Resource subparsers will be added in later tasks via `register(subparsers, cache)` functions in each `kz/<resource>.py`.

- [ ] **Step 1: Write failing test `tests/test_cli_skeleton.py`.**

```python
import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")


def run(*args, env_extra=None):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        env=env, capture_output=True, text=True,
    )


class TestSkeleton(unittest.TestCase):
    def test_no_args_prints_help_exit_2(self):
        r = run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage:", r.stderr.lower() + r.stdout.lower())

    def test_help_lists_global_flags(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--board", r.stdout)
        self.assertIn("--no-cache", r.stdout)
        self.assertIn("--pretty", r.stdout)
        self.assertIn("--api-token", r.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure (the v2 script won't have the new flags).**

```bash
python3 -m unittest tests.test_cli_skeleton -v
```
Expected: FAIL on flag presence.

- [ ] **Step 3: Replace `scripts/kanban_zone_api.py` with the new skeleton.**

```python
#!/usr/bin/env python3
"""Kanban Zone CLI — v3 entry point.

Resource handlers live in scripts/kz/<resource>.py. Each resource module
exposes register(subparsers, ctx) that wires its grouped subparser into
the shared dispatcher.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kz import http as kz_http  # noqa: E402
from kz import output as kz_output  # noqa: E402
from kz.cache import Cache  # noqa: E402


def _load_env_file():
    candidates = [os.getcwd(), os.path.dirname(HERE)]
    for d in candidates:
        path = os.path.join(d, ".env")
        if os.path.isfile(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)


def _cache_path():
    override = os.environ.get("KANBANZONE_CACHE_PATH")
    if override:
        return override
    return os.path.expanduser("~/.kanbanzone-cache.json")


class Context:
    def __init__(self, args):
        self.board = args.board or os.environ.get("KANBAN_ZONE_BOARD_ID")
        self.pretty = args.pretty
        self.cache = Cache(_cache_path(), enabled=not args.no_cache)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="kanban_zone_api.py",
        description="Kanban Zone CLI (v3, wraps API v1.4).",
    )
    parser.add_argument("--board", help="Override KANBAN_ZONE_BOARD_ID for this call.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass the local cache; do not read or write it.")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON output.")
    parser.add_argument("--api-token", help="Override KANBAN_ZONE_API_KEY for this call.")

    sub = parser.add_subparsers(dest="group")
    sub.required = True

    # Resource registrations are added in later tasks:
    # from kz import boards, cards, comments, ...
    # boards.register(sub)
    # cards.register(sub)
    # ...
    # legacy.register(sub)

    return parser


def main(argv=None):
    _load_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.api_token:
        kz_http.set_api_token(args.api_token)
    ctx = Context(args)
    try:
        return args.func(args, ctx)
    except kz_http.KZApiError as exc:
        kz_output.error_exit(str(exc), status=exc.status)
    except (kz_http.KZAuthError, ValueError) as exc:
        kz_output.error_exit(str(exc))


if __name__ == "__main__":
    sys.exit(main() or 0)
```

Note: `main()` returns whatever the resource handler returned. `cmd_verify_signature` returns 0/1 to set the process exit code; every other handler returns `None` (treated as 0). The `or 0` guard keeps successful runs at exit code 0.

- [ ] **Step 4: Run — expect failure on `args.func` (no resources registered yet means subparser is empty).**

The skeleton test only checks help output, which should now pass:

```bash
python3 -m unittest tests.test_cli_skeleton -v
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kanban_zone_api.py tests/test_cli_skeleton.py
git commit -m "$(cat <<'EOF'
Replace v2 monolith with v3 CLI entry skeleton

## Problem
v3 splits into a kz/ package with per-resource subparsers. The entry
script needs to be rewritten as pure dispatch: load .env, parse global
flags, build a Context (board, cache, pretty), then hand off to whichever
resource handler argparse selected.

## Solution
scripts/kanban_zone_api.py is now ~80 lines. Global flags --board,
--no-cache, --pretty, --api-token live on the root parser. _load_env_file
keeps v2 behaviour (CWD then skill parent). Cache path is
~/.kanbanzone-cache.json by default, override via KANBANZONE_CACHE_PATH.
Resource registrations are stubbed; they are wired in per-resource tasks.

## Verified
python3 -m unittest tests.test_cli_skeleton passes (2 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Resources

Each resource module follows the same template:

1. Define handler functions taking `(args, ctx)` and calling `kz.http.api_request`.
2. Define `register(subparsers)` that adds the resource's group subparser, then per-subcommand subparsers under it, each calling `set_defaults(func=handler_fn)`.
3. Tests use `FakeApi`, asserting the right method/path/params/body and that handlers print the response via `kz.output.print_json`.

Wiring each resource into the entry script is its own commit (touches `scripts/kanban_zone_api.py`).

For brevity in this plan, **fixture JSON files are introduced just-in-time** — when a test references `tests/fixtures/<name>.json`, that step also writes the fixture. Fixtures are *minimal but real-shape* (4-6 fields, real types, sanitized).

---

### Task 9: Org module (`kz.org`)

**Endpoints:** `GET /me`, `GET /organization`. Two handlers, two subcommands. This is the simplest resource and establishes the pattern every other resource follows.

**Files:**
- Create: `scripts/kz/org.py`
- Create: `tests/test_org.py`
- Modify: `scripts/kanban_zone_api.py` (register org group)

- [ ] **Step 1: Write failing tests `tests/test_org.py`.**

```python
import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import org as kz_org
from tests.fakes import FakeApi


class _StubCtx:
    def __init__(self, pretty=False):
        self.pretty = pretty
        self.board = "BOARDX"
        self.cache = None


class TestOrg(unittest.TestCase):
    def test_me_calls_get_me_and_prints(self):
        buf = io.StringIO()
        with FakeApi() as fake, patch("sys.stdout", buf):
            fake.expect("GET", "/me").returns({"organization": "Acme"})
            kz_org.cmd_me(args=None, ctx=_StubCtx())
        self.assertIn('"organization": "Acme"', buf.getvalue())

    def test_context_sends_include_flags(self):
        buf = io.StringIO()
        ns = type("N", (), {
            "include_boards": True, "include_members": False,
            "include_columns": False, "include_labels": False,
            "include_custom_fields": True,
        })()
        with FakeApi() as fake, patch("sys.stdout", buf):
            fake.expect("GET", "/organization", params={
                "includeBoards": True, "includeMembers": False,
                "includeColumns": False, "includeLabels": False,
                "includeCustomFields": True,
            }).returns({"name": "Acme"})
            kz_org.cmd_context(args=ns, ctx=_StubCtx())
        self.assertIn('"name": "Acme"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_org -v
```
Expected: ImportError on `kz.org`.

- [ ] **Step 3: Implement `scripts/kz/org.py`.**

```python
"""Organization context — /me, /organization."""
from kz import http as kz_http
from kz import output as kz_output


def cmd_me(args, ctx):
    resp = kz_http.api_request("GET", "/me")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_context(args, ctx):
    params = {
        "includeBoards": args.include_boards,
        "includeMembers": args.include_members,
        "includeColumns": args.include_columns,
        "includeLabels": args.include_labels,
        "includeCustomFields": args.include_custom_fields,
    }
    resp = kz_http.api_request("GET", "/organization", params=params)
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("org", help="Organization context (me, context).")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    me = sub.add_parser("me", help="Verify the API key works.")
    me.set_defaults(func=cmd_me)

    ctx = sub.add_parser("context", help="Get organization context with optional includes.")
    ctx.add_argument("--include-boards", action="store_true")
    ctx.add_argument("--include-members", action="store_true")
    ctx.add_argument("--include-columns", action="store_true")
    ctx.add_argument("--include-labels", action="store_true")
    ctx.add_argument("--include-custom-fields", action="store_true")
    ctx.set_defaults(func=cmd_context)
```

- [ ] **Step 4: Wire org into the entry script.** In `scripts/kanban_zone_api.py`, replace the `# Resource registrations` comment block with:

```python
    from kz import org  # noqa: E402
    org.register(sub)
```

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_org -v
```
Expected: 2 tests PASS.

- [ ] **Step 6: Smoke-test the wired CLI.**

```bash
python3 scripts/kanban_zone_api.py org --help
```
Expected: shows `me` and `context` subcommands.

- [ ] **Step 7: Commit.**

```bash
git add scripts/kz/org.py scripts/kanban_zone_api.py tests/test_org.py
git commit -m "$(cat <<'EOF'
Add org group (me, context)

## Problem
v1.4 exposes /me and /organization for plan/feature/board discovery; v2
had no equivalent.

## Solution
kz/org.py implements cmd_me and cmd_context, both sending args.pretty
through to print_json. context surfaces all five include flags
(--include-boards/-members/-columns/-labels/-custom-fields). Wired into
the entry script.

## Verified
python3 -m unittest tests.test_org passes (2 tests).
python3 scripts/kanban_zone_api.py org --help renders.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Boards module (`kz.boards`)

**Endpoints:** `GET /boards`, `GET /boards/{publicId}`, `GET /boards/{publicId}/columns`, `GET /boards/{publicId}/labels`, `GET /boards/{publicId}/members`, `GET /boards/{publicId}/custom-fields`, `GET /templates/{publicId}`. Seven subcommands: `list`, `get`, `columns`, `labels`, `members`, `custom-fields`, `templates`.

**Files:**
- Create: `scripts/kz/boards.py`
- Create: `tests/test_boards.py`
- Create: `tests/fixtures/boards_list.json`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write the fixture `tests/fixtures/boards_list.json`.**

```json
{
  "count": 1,
  "boards": [
    {
      "publicId": "BOARD1",
      "name": "Roadmap",
      "isArchived": false,
      "activeCardsCount": 12,
      "blockedCardsCount": 1
    }
  ]
}
```

- [ ] **Step 2: Write failing tests `tests/test_boards.py`.**

```python
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
```

- [ ] **Step 3: Run — expect failure.**

```bash
python3 -m unittest tests.test_boards -v
```
Expected: ImportError.

- [ ] **Step 4: Implement `scripts/kz/boards.py`.**

```python
"""Boards group: list, get, columns, labels, members, custom-fields, templates."""
from kz import http as kz_http
from kz import output as kz_output


def _require_board(ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return ctx.board


def cmd_list(args, ctx):
    resp = kz_http.api_request("GET", "/boards", params={
        "includeArchived": args.include_archived,
        "includeColumns": args.include_columns,
    })
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}", params={
        "includeColumns": args.include_columns,
        "includeMembers": args.include_members,
        "includeLabels": args.include_labels,
        "includeCustomFields": args.include_custom_fields,
    })
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_columns(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/columns")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_labels(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/labels")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_members(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/members")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_custom_fields(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/boards/{board}/custom-fields")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_templates(args, ctx):
    board = _require_board(ctx)
    resp = kz_http.api_request("GET", f"/templates/{board}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("boards", help="Board listing and sub-resources.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("list", help="List all boards.")
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--include-columns", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get a board by --board.")
    p.add_argument("--include-columns", action="store_true")
    p.add_argument("--include-members", action="store_true")
    p.add_argument("--include-labels", action="store_true")
    p.add_argument("--include-custom-fields", action="store_true")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("columns", help="List columns for --board.")
    p.set_defaults(func=cmd_columns)

    p = sub.add_parser("labels", help="List labels for --board.")
    p.set_defaults(func=cmd_labels)

    p = sub.add_parser("members", help="List members for --board.")
    p.set_defaults(func=cmd_members)

    p = sub.add_parser("custom-fields", help="List custom fields for --board.")
    p.set_defaults(func=cmd_custom_fields)

    p = sub.add_parser("templates", help="List card templates for --board.")
    p.set_defaults(func=cmd_templates)
```

- [ ] **Step 5: Wire into entry script.** Add `from kz import boards` next to the org import and call `boards.register(sub)`.

- [ ] **Step 6: Run — expect pass.**

```bash
python3 -m unittest tests.test_boards -v
```
Expected: 9 tests PASS.

- [ ] **Step 7: Commit.**

```bash
git add scripts/kz/boards.py tests/test_boards.py tests/fixtures/boards_list.json scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add boards group with sub-resources and templates

## Problem
v1.4 introduces /boards/{publicId}/columns|labels|members|custom-fields
and /templates/{publicId}. v2 only had `boards` and `board` (the latter
now deprecated as /board/{board}).

## Solution
kz/boards.py implements 7 handlers (list, get, columns, labels, members,
custom-fields, templates). list calls /boards; get and the sub-resource
endpoints all use the new /boards/{publicId} paths. templates is grouped
here because templates are board-scoped, not org-scoped.

## Verified
python3 -m unittest tests.test_boards passes (9 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Cards module — read handlers (`list`, `get`, `history`, `metrics`)

**Endpoints:** `GET /cards`, `GET /cards/{id}`, `GET /cards/{id}/history`, `GET /cards/{id}/metrics`. Cards is the largest module; it's split across three tasks (read / write / cross-cutting). This task covers reads.

**Files:**
- Create: `scripts/kz/cards.py`
- Create: `tests/test_cards_read.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_cards_read.py`.**

```python
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import cards as kz_cards
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class _Ctx:
    def __init__(self, board="BOARD1"):
        self.board = board
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardsRead(unittest.TestCase):
    def test_list_default_filters(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"count": 0, "cards": [], "hasMore": False, "totalAvailable": 0})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label=None, owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())

    def test_list_passes_days_since_last_update(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100,
                "includeArchived": False, "daysSinceLastUpdate": 7,
            }).returns({"count": 0, "cards": [], "hasMore": False, "totalAvailable": 0})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=7,
                    label=None, owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())

    def test_list_client_side_filter_by_label(self):
        with FakeApi() as fake:
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "count": 2, "totalAvailable": 2, "hasMore": False,
                "cards": [
                    {"number": 1, "label": "Bug", "title": "x"},
                    {"number": 2, "label": "Feature", "title": "y"},
                ],
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_list(_ns(
                    page=1, count=100, include_archived=False, days_since_last_update=None,
                    label="Bug", owner=None, column=None, priority=None, blocked=False, query=None,
                ), _Ctx())
        self.assertIn('"number": 1', buf.getvalue())
        self.assertNotIn('"number": 2', buf.getvalue())

    def test_get_by_number_resolves_then_calls_oid_endpoint(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_get(_ns(id="42"), ctx)

    def test_get_by_object_id_skips_resolution(self):
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}").returns({"_id": CARD_OID, "number": 42})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_get(_ns(id=CARD_OID), _Ctx())

    def test_history_uses_oid_and_passes_from(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/history",
                        params={"from": "2025-01-01"}).returns([])
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_history(_ns(id="42", from_date="2025-01-01"), ctx)

    def test_metrics_uses_oid(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/metrics").returns({"cycle": 1.5})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_metrics(_ns(id="42"), ctx)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_cards_read -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/kz/cards.py` (read-only handlers + register stub for the group).**

```python
"""Cards group. Split across three logical sections: read, write, cross-cutting.

This file holds all card subcommands; they are grouped here for cohesion since
they share helpers (board resolution, OID resolution, client-side filters)."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _require_board(ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return ctx.board


def _resolve(ctx, value):
    return kz_ids.resolve_card_object_id(value, _require_board(ctx), ctx.cache)


def _get_field(card, name):
    if name in card:
        return card[name]
    return (card.get("custom") or {}).get(name)


def _filter_cards(cards, label=None, owner=None, column=None, priority=None,
                  blocked=False, query=None):
    out = []
    for c in cards:
        if label and _get_field(c, "label") != label:
            continue
        if owner and _get_field(c, "owner") != owner:
            continue
        if column:
            colname = c.get("columnTitle") or c.get("column")
            if colname != column:
                continue
        if priority is not None and str(_get_field(c, "priority")) != str(priority):
            continue
        if blocked and not c.get("blocked"):
            continue
        if query:
            haystack = " ".join(str(c.get(k, "")) for k in ("title", "description"))
            if query.lower() not in haystack.lower():
                continue
        out.append(c)
    return out


def cmd_list(args, ctx):
    board = _require_board(ctx)
    params = {
        "board": board, "page": args.page, "count": args.count,
        "includeArchived": args.include_archived,
    }
    if args.days_since_last_update is not None:
        params["daysSinceLastUpdate"] = args.days_since_last_update
    resp = kz_http.api_request("GET", "/cards", params=params)
    if any([args.label, args.owner, args.column, args.priority, args.blocked, args.query]):
        resp = dict(resp or {})
        cards = _filter_cards(
            resp.get("cards", []),
            label=args.label, owner=args.owner, column=args.column,
            priority=args.priority, blocked=args.blocked, query=args.query,
        )
        resp["cards"] = cards
        resp["count"] = len(cards)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    oid = _resolve(ctx, args.id)
    resp = kz_http.api_request("GET", f"/cards/{oid}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_history(args, ctx):
    oid = _resolve(ctx, args.id)
    params = {}
    if args.from_date:
        params["from"] = args.from_date
    resp = kz_http.api_request("GET", f"/cards/{oid}/history", params=params or None)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_metrics(args, ctx):
    oid = _resolve(ctx, args.id)
    resp = kz_http.api_request("GET", f"/cards/{oid}/metrics")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("cards", help="Card CRUD, history, metrics, links, search.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("list", help="List cards on the active board.")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--days-since-last-update", type=int, default=None)
    p.add_argument("--label")
    p.add_argument("--owner")
    p.add_argument("--column")
    p.add_argument("--priority")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--query")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get one card by number or ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("history", help="Card history.")
    p.add_argument("--id", required=True)
    p.add_argument("--from-date", help="ISO date.")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("metrics", help="Card metrics.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_metrics)
```

- [ ] **Step 4: Wire into entry script.** Add `from kz import cards` and `cards.register(sub)`.

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_cards_read -v
```
Expected: 7 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/cards.py tests/test_cards_read.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add cards group: list, get, history, metrics

## Problem
v1.4 cards endpoints use ObjectId-keyed flat URLs and add /history and
/metrics. v2 only had number-keyed list/get/create/update/move.

## Solution
kz/cards.py read handlers: cmd_list calls GET /cards with pagination and
optional client-side filters (label/owner/column/priority/blocked/query)
preserved from v2. cmd_get/cmd_history/cmd_metrics resolve the --id flag
through kz.ids and call the new ObjectId paths. register wires the cards
group with these four subcommands; write handlers come in the next task.

## Verified
python3 -m unittest tests.test_cards_read passes (7 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Cards module — write handlers (`create`, `create-bulk`, `update`, `move`, `delete`)

**Endpoints:** `POST /cards`, `PATCH /cards/{id}`, `POST /cards/{id}/move`, `DELETE /cards/{id}`. The bulk variant is also `POST /cards` (with multiple cards in body — same shape as v2's `create-cards`).

**Files:**
- Modify: `scripts/kz/cards.py`
- Create: `tests/test_cards_write.py`

- [ ] **Step 1: Write failing tests `tests/test_cards_write.py`.**

```python
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import cards as kz_cards
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardsWrite(unittest.TestCase):
    def test_create_minimal(self):
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={
                "board": "BOARD1", "addToTop": False,
                "cards": [{"title": "X"}],
            }).returns({"cardsAdded": 1, "cards": [{"_id": CARD_OID, "number": 7}]})
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_create(_ns(
                    title="X", description=None, description_file=None,
                    column_id=None, owner=None, priority=None, label=None,
                    size=None, due_at=None, blocked=False, blocked_reason=None,
                    add_to_top=False, watcher=[], custom_field=[], template_id=None,
                ), _Ctx())
            self.assertIn('"cardsAdded": 1', buf.getvalue())

    def test_create_with_watchers_and_custom_fields(self):
        with FakeApi() as fake:
            fake.expect("POST", "/cards", body={
                "board": "BOARD1", "addToTop": True,
                "cards": [{
                    "title": "X", "watchers": ["a@b.com", "c@d.com"],
                    "customFields": [{"label": "Sprint", "value": "42"}],
                }],
            }).returns({"cardsAdded": 1, "cards": []})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_create(_ns(
                    title="X", description=None, description_file=None,
                    column_id=None, owner=None, priority=None, label=None,
                    size=None, due_at=None, blocked=False, blocked_reason=None,
                    add_to_top=True, watcher=["a@b.com", "c@d.com"],
                    custom_field=["Sprint=42"], template_id=None,
                ), _Ctx())

    def test_create_bulk_from_file(self):
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "cards.json")
            with open(fpath, "w") as f:
                json.dump({"board": "BOARD1", "cards": [{"title": "A"}, {"title": "B"}]}, f)
            with FakeApi() as fake:
                fake.expect("POST", "/cards", body={
                    "board": "BOARD1", "cards": [{"title": "A"}, {"title": "B"}],
                }).returns({"cardsAdded": 2, "cards": []})
                with patch("sys.stdout", io.StringIO()):
                    kz_cards.cmd_create_bulk(_ns(file=fpath), _Ctx())

    def test_update_uses_patch_after_resolution(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1", "title": "New",
            }).returns({"_id": CARD_OID, "number": 42, "title": "New"})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_update(_ns(
                    id="42", title="New", description=None, description_file=None,
                    owner=None, priority=None, label=None, size=None, due_at=None,
                    blocked=None, blocked_reason=None, watcher=[], custom_field=[],
                ), ctx)

    def test_update_blocked_true_includes_reason(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1", "blocked": True, "blockedReason": "waiting",
            }).returns({"_id": CARD_OID})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_update(_ns(
                    id="42", title=None, description=None, description_file=None,
                    owner=None, priority=None, label=None, size=None, due_at=None,
                    blocked=True, blocked_reason="waiting", watcher=[], custom_field=[],
                ), ctx)

    def test_move_uses_post_move(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", f"/cards/{CARD_OID}/move", body={
                "board": "BOARD1", "columnId": "COL2", "addToTop": False,
            }).returns({"_id": CARD_OID, "columnId": "COL2"})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_move(_ns(id="42", column_id="COL2", add_to_top=False), ctx)

    def test_delete_invalidates_cache(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("DELETE", f"/cards/{CARD_OID}",
                        params={"board": "BOARD1"}).returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_delete(_ns(id="42"), ctx)
        self.assertIsNone(ctx.cache.get_card_oid("BOARD1", 42))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_cards_write -v
```
Expected: AttributeError on missing handler.

- [ ] **Step 3: Append write handlers to `scripts/kz/cards.py`.** After `cmd_metrics` and before `def register`:

```python
def _parse_custom_fields(raw_list):
    out = []
    for raw in raw_list or []:
        if "=" not in raw:
            raise ValueError(f"--custom-field must be Key=Value, got {raw!r}")
        k, v = raw.split("=", 1)
        out.append({"label": k.strip(), "value": v.strip()})
    return out


def _read_description(args):
    if getattr(args, "description_file", None):
        with open(args.description_file) as f:
            return f.read()
    return getattr(args, "description", None)


def _card_input(args, include_title=True):
    body = {}
    if include_title and getattr(args, "title", None):
        body["title"] = args.title
    desc = _read_description(args)
    if desc is not None:
        body["description"] = desc
    for src, dst in [("column_id", "columnId"), ("owner", "owner"),
                     ("priority", "priority"), ("label", "label"),
                     ("size", "size"), ("due_at", "dueAt"),
                     ("blocked_reason", "blockedReason"),
                     ("template_id", "templateId")]:
        v = getattr(args, src, None)
        if v is not None:
            body[dst] = v
    blocked = getattr(args, "blocked", None)
    if blocked is True:
        body["blocked"] = True
    elif blocked is False and "blocked" in vars(args):
        # explicit false from update - only include if user passed --blocked false
        pass
    if getattr(args, "watcher", None):
        body["watchers"] = list(args.watcher)
    cf = _parse_custom_fields(getattr(args, "custom_field", None))
    if cf:
        body["customFields"] = cf
    return body


def cmd_create(args, ctx):
    board = _require_board(ctx)
    body = {"board": board, "addToTop": bool(getattr(args, "add_to_top", False)),
            "cards": [_card_input(args, include_title=True)]}
    resp = kz_http.api_request("POST", "/cards", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_create_bulk(args, ctx):
    with open(args.file) as f:
        payload = __import__("json").load(f)
    if "board" not in payload:
        payload["board"] = _require_board(ctx)
    resp = kz_http.api_request("POST", "/cards", body=payload)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = _card_input(args, include_title=True)
    body["board"] = board
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_move(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "columnId": args.column_id,
            "addToTop": bool(getattr(args, "add_to_top", False))}
    resp = kz_http.api_request("POST", f"/cards/{oid}/move", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    kz_http.api_request("DELETE", f"/cards/{oid}", params={"board": board})
    ctx.cache.invalidate_card(board, oid)
    kz_output.print_json({"deleted": True, "id": oid}, pretty=ctx.pretty)
```

Then extend the existing `register` function — append these subparsers after the `metrics` parser:

```python
    p = sub.add_parser("create", help="Create a card.")
    p.add_argument("--title", required=True)
    p.add_argument("--description")
    p.add_argument("--description-file")
    p.add_argument("--column-id")
    p.add_argument("--owner")
    p.add_argument("--priority")
    p.add_argument("--label")
    p.add_argument("--size")
    p.add_argument("--due-at")
    p.add_argument("--blocked", action="store_true")
    p.add_argument("--blocked-reason")
    p.add_argument("--add-to-top", action="store_true")
    p.add_argument("--watcher", action="append", default=[])
    p.add_argument("--custom-field", action="append", default=[])
    p.add_argument("--template-id")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("create-bulk", help="Create many cards from a JSON file.")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_create_bulk)

    p = sub.add_parser("update", help="Update a card by --id (number or OID).")
    p.add_argument("--id", required=True)
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--description-file")
    p.add_argument("--owner")
    p.add_argument("--priority")
    p.add_argument("--label")
    p.add_argument("--size")
    p.add_argument("--due-at")
    p.add_argument("--blocked", type=lambda s: s.lower() == "true", default=None)
    p.add_argument("--blocked-reason")
    p.add_argument("--watcher", action="append", default=[])
    p.add_argument("--custom-field", action="append", default=[])
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("move", help="Move a card to a column.")
    p.add_argument("--id", required=True)
    p.add_argument("--column-id", required=True)
    p.add_argument("--add-to-top", action="store_true")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("delete", help="Delete a card by --id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_cards_write -v
```
Expected: 7 tests PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/cards.py tests/test_cards_write.py
git commit -m "$(cat <<'EOF'
Add cards write handlers (create, create-bulk, update, move, delete)

## Problem
v1.4 deprecates PUT /card/{id} in favor of PATCH /cards/{id}, and adds
DELETE /cards/{id}. v2 has no delete and uses the deprecated PUT path.
Bulk-create needs to read JSON from --file (preserve v2 shape).

## Solution
cmd_update calls PATCH after resolving the --id through kz.ids; cmd_move
keeps the existing /move semantics under the new flat path. cmd_delete
calls DELETE and invalidates the cache entry. Shared _card_input helper
builds the body with watchers/custom-fields and HTML description from
--description-file. cmd_create_bulk reads the v2 JSON shape unchanged.

## Verified
python3 -m unittest tests.test_cards_write passes (7 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Cards module — links + search + wip-check

**Endpoints used:** `PATCH /cards/{id}` (with `links` sub-schema for add/remove), plus client-side cross-board scan for search and WIP check.

**Files:**
- Modify: `scripts/kz/cards.py`
- Create: `tests/test_cards_misc.py`

- [ ] **Step 1: Write failing tests `tests/test_cards_misc.py`.**

```python
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import cards as kz_cards
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestCardLinks(unittest.TestCase):
    def test_links_add_card(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"add": [{"card": 99, "type": "related"}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_links_add(_ns(
                    id="42", card=99, url=None, title=None, type="related",
                ), ctx)

    def test_links_add_url(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"add": [{"url": "https://x", "title": "Spec",
                                    "type": "external"}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_links_add(_ns(
                    id="42", card=None, url="https://x", title="Spec", type="external",
                ), ctx)

    def test_links_remove_card(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("PATCH", f"/cards/{CARD_OID}", body={
                "board": "BOARD1",
                "links": {"remove": [{"card": 99}]},
            }).returns({})
            with patch("sys.stdout", io.StringIO()):
                kz_cards.cmd_links_remove(_ns(
                    id="42", card=99, url=None,
                ), ctx)


class TestCardsSearch(unittest.TestCase):
    def test_search_iterates_all_boards(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards", params={"includeArchived": False}).returns({
                "boards": [{"publicId": "B1", "name": "One"},
                           {"publicId": "B2", "name": "Two"}],
            })
            fake.expect("GET", "/cards", params={
                "board": "B1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"number": 1, "title": "deploy soon"}],
                        "hasMore": False})
            fake.expect("GET", "/cards", params={
                "board": "B2", "page": 1, "count": 100, "includeArchived": False,
            }).returns({"cards": [{"number": 2, "title": "buy lunch"}],
                        "hasMore": False})
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_search(_ns(query="deploy", label=None, owner=None), _Ctx())
            self.assertIn('"deploy soon"', buf.getvalue())
            self.assertNotIn('"buy lunch"', buf.getvalue())


class TestWipCheck(unittest.TestCase):
    def test_wip_check_flags_violations(self):
        with FakeApi() as fake:
            fake.expect("GET", "/boards/BOARD1", params={
                "includeColumns": True, "includeMembers": False,
                "includeLabels": False, "includeCustomFields": False,
            }).returns({
                "publicId": "BOARD1",
                "columns": [
                    {"_id": "c1", "title": "Backlog", "minWIP": 0, "maxWIP": 10},
                    {"_id": "c2", "title": "Doing", "minWIP": 1, "maxWIP": 3},
                ],
            })
            fake.expect("GET", "/cards", params={
                "board": "BOARD1", "page": 1, "count": 100, "includeArchived": False,
            }).returns({
                "cards": [
                    {"columnId": "c2"}, {"columnId": "c2"}, {"columnId": "c2"},
                    {"columnId": "c2"}, {"columnId": "c2"},
                ],
                "hasMore": False,
            })
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                kz_cards.cmd_wip_check(_ns(), _Ctx())
            self.assertIn('"violation"', buf.getvalue())
            self.assertIn('"Doing"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure.**

```bash
python3 -m unittest tests.test_cards_misc -v
```
Expected: AttributeError.

- [ ] **Step 3: Append handlers + register entries to `scripts/kz/cards.py`.**

```python
def _links_payload(action, args):
    if args.card is not None:
        item = {"card": int(args.card)}
        if action == "add":
            item["type"] = args.type or "related"
        return {action: [item]}
    if args.url:
        item = {"url": args.url}
        if action == "add":
            item["title"] = args.title or args.url
            item["type"] = args.type or "external"
        return {action: [item]}
    raise ValueError("Provide either --card or --url")


def cmd_links_add(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "links": _links_payload("add", args)}
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_links_remove(args, ctx):
    board = _require_board(ctx)
    oid = _resolve(ctx, args.id)
    body = {"board": board, "links": _links_payload("remove", args)}
    resp = kz_http.api_request("PATCH", f"/cards/{oid}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def _fetch_all_cards(board, include_archived=False):
    page = 1
    out = []
    while True:
        resp = kz_http.api_request("GET", "/cards", params={
            "board": board, "page": page, "count": 100,
            "includeArchived": include_archived,
        }) or {}
        out.extend(resp.get("cards", []))
        if not resp.get("hasMore"):
            break
        page += 1
    return out


def cmd_search(args, ctx):
    boards_resp = kz_http.api_request("GET", "/boards",
                                       params={"includeArchived": False}) or {}
    matches = []
    for b in boards_resp.get("boards", []):
        cards = _fetch_all_cards(b["publicId"])
        filtered = _filter_cards(
            cards, label=args.label, owner=args.owner, query=args.query,
        )
        for c in filtered:
            c2 = dict(c)
            c2["_board"] = b["publicId"]
            c2["_boardName"] = b.get("name")
            matches.append(c2)
    kz_output.print_json({"count": len(matches), "cards": matches},
                          pretty=ctx.pretty)


def cmd_wip_check(args, ctx):
    board = _require_board(ctx)
    board_resp = kz_http.api_request("GET", f"/boards/{board}", params={
        "includeColumns": True, "includeMembers": False,
        "includeLabels": False, "includeCustomFields": False,
    }) or {}
    cards = _fetch_all_cards(board)
    counts = {}
    for c in cards:
        cid = c.get("columnId") or c.get("column")
        counts[cid] = counts.get(cid, 0) + 1
    report = []
    for col in board_resp.get("columns", []):
        cid = col.get("_id") or col.get("columnId")
        n = counts.get(cid, 0)
        min_w = col.get("minWIP") or 0
        max_w = col.get("maxWIP") or 0
        status = "ok"
        if max_w and n > max_w:
            status = "violation"
        elif min_w and n < min_w:
            status = "below_min"
        report.append({
            "columnId": cid, "title": col.get("title"),
            "current": n, "minWIP": min_w, "maxWIP": max_w, "status": status,
        })
    kz_output.print_json({"board": board, "columns": report},
                          pretty=ctx.pretty)
```

Append these subparser entries to `register` after the `delete` parser:

```python
    p = sub.add_parser("links-add", help="Add a card-to-card or URL link.")
    p.add_argument("--id", required=True)
    p.add_argument("--card", type=int)
    p.add_argument("--url")
    p.add_argument("--title")
    p.add_argument("--type", default=None)
    p.set_defaults(func=cmd_links_add)

    p = sub.add_parser("links-remove", help="Remove a card-to-card or URL link.")
    p.add_argument("--id", required=True)
    p.add_argument("--card", type=int)
    p.add_argument("--url")
    p.set_defaults(func=cmd_links_remove)

    p = sub.add_parser("search", help="Cross-board card search.")
    p.add_argument("--query")
    p.add_argument("--label")
    p.add_argument("--owner")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("wip-check", help="Compare counts to per-column WIP limits.")
    p.set_defaults(func=cmd_wip_check)
```

- [ ] **Step 4: Run — expect pass.**

```bash
python3 -m unittest tests.test_cards_misc -v
```
Expected: 5 tests PASS.

- [ ] **Step 5: Commit.**

```bash
git add scripts/kz/cards.py tests/test_cards_misc.py
git commit -m "$(cat <<'EOF'
Add cards links/search/wip-check on PATCH endpoint

## Problem
v2 used PUT /card/{id} for the links sub-schema; v1.4 wants PATCH /cards/{id}.
Cross-board search and WIP check are kept (v2 features) but updated to use
new /boards/{publicId}/...

## Solution
cmd_links_add and cmd_links_remove construct {board, links: {add|remove:[...]}}
and call PATCH on the resolved ObjectId. cmd_search iterates GET /boards
then pages /cards per board and filters client-side. cmd_wip_check uses
GET /boards/{publicId}?includeColumns=true plus the same paged scan.

## Verified
python3 -m unittest tests.test_cards_misc passes (5 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Comments module (`kz.comments`)

**Endpoints:** `POST /comments`, `GET /cards/{id}/comments`. Two subcommands: `add`, `list`.

**Files:**
- Create: `scripts/kz/comments.py`
- Create: `tests/test_comments.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_comments.py`.**

```python
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import comments as kz_comments
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestComments(unittest.TestCase):
    def test_add_resolves_card_and_uses_flat_url(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/comments", body={
                "card": CARD_OID, "text": "hello",
            }).returns({"_id": "C1"})
            with patch("sys.stdout", io.StringIO()):
                kz_comments.cmd_add(_ns(card="42", text="hello", text_file=None), ctx)

    def test_add_text_from_file(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "t.txt")
            with open(f, "w") as fh:
                fh.write("from file")
            with FakeApi() as fake:
                fake.expect("POST", "/comments", body={
                    "card": CARD_OID, "text": "from file",
                }).returns({"_id": "C1"})
                with patch("sys.stdout", io.StringIO()):
                    kz_comments.cmd_add(_ns(card="42", text=None, text_file=f), ctx)

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/comments").returns([{"_id": "C1"}])
            with patch("sys.stdout", io.StringIO()):
                kz_comments.cmd_list(_ns(card="42"), ctx)

    def test_add_requires_text_or_file(self):
        ctx = _Ctx()
        with self.assertRaises(ValueError):
            kz_comments.cmd_add(_ns(card="42", text=None, text_file=None), ctx)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect ImportError.**

```bash
python3 -m unittest tests.test_comments -v
```

- [ ] **Step 3: Implement `scripts/kz/comments.py`.**

```python
"""Comments group: add, list."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _resolve(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kz_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def _read_text(args):
    if args.text_file:
        with open(args.text_file) as f:
            return f.read()
    return args.text


def cmd_add(args, ctx):
    text = _read_text(args)
    if text is None:
        raise ValueError("Provide --text or --text-file")
    oid = _resolve(ctx, args.card)
    resp = kz_http.api_request("POST", "/comments", body={"card": oid, "text": text})
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve(ctx, args.card)
    resp = kz_http.api_request("GET", f"/cards/{oid}/comments")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("comments", help="Card comments.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("add", help="Add a comment to a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="List comments on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
```

- [ ] **Step 4: Wire `comments.register(sub)` in `scripts/kanban_zone_api.py`.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_comments -v
```
Expected: 4 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/comments.py tests/test_comments.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add comments group (add, list)

## Problem
v1.4 introduces POST /comments (flat URL with card in body) and
GET /cards/{id}/comments. v2 had no comment commands.

## Solution
kz/comments.py exposes add/list. add reads text from --text or
--text-file; both resolve --card via kz.ids and call the new flat URL.

## Verified
python3 -m unittest tests.test_comments passes (4 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Checklists module (`kz.checklists`)

**Endpoints:** `POST /checklists`, `PATCH /checklists/{id}`, `DELETE /checklists/{id}`, `GET /cards/{id}/checklists`. Subcommands: `create`, `update`, `delete`, `list`.

**Files:**
- Create: `scripts/kz/checklists.py`
- Create: `tests/test_checklists.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_checklists.py`.**

```python
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import checklists as kz_chk
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"
CHK_ID = "abcd1234ef5678901234abcd"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestChecklists(unittest.TestCase):
    def test_create_minimal(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/checklists", body={
                "card": CARD_OID, "title": "Pre-flight",
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_create(_ns(card="42", title="Pre-flight", task=[]), ctx)

    def test_create_with_inline_tasks(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/checklists", body={
                "card": CARD_OID, "title": "QA",
                "tasks": [{"description": "First"}, {"description": "Second"}],
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_create(_ns(
                    card="42", title="QA", task=["First", "Second"],
                ), ctx)

    def test_update_renames(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/checklists/{CHK_ID}", body={
                "title": "Renamed",
            }).returns({"_id": CHK_ID, "title": "Renamed"})
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_update(_ns(id=CHK_ID, title="Renamed", position=None), _Ctx())

    def test_update_position(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/checklists/{CHK_ID}", body={
                "position": 1,
            }).returns({"_id": CHK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_update(_ns(id=CHK_ID, title=None, position=1), _Ctx())

    def test_delete(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/checklists/{CHK_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_delete(_ns(id=CHK_ID), _Ctx())

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/checklists").returns([])
            with patch("sys.stdout", io.StringIO()):
                kz_chk.cmd_list(_ns(card="42"), ctx)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect ImportError.**

- [ ] **Step 3: Implement `scripts/kz/checklists.py`.**

```python
"""Checklists group: create, update, delete, list."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _resolve_card(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kz_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def cmd_create(args, ctx):
    oid = _resolve_card(ctx, args.card)
    body = {"card": oid, "title": args.title}
    if args.task:
        body["tasks"] = [{"description": t} for t in args.task]
    resp = kz_http.api_request("POST", "/checklists", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.title is not None:
        body["title"] = args.title
    if args.position is not None:
        body["position"] = args.position
    if not body:
        raise ValueError("Provide at least one of --title or --position")
    resp = kz_http.api_request("PATCH", f"/checklists/{args.id}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kz_http.api_request("DELETE", f"/checklists/{args.id}")
    kz_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve_card(ctx, args.card)
    resp = kz_http.api_request("GET", f"/cards/{oid}/checklists")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("checklists", help="Card checklists.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("create", help="Create a checklist on a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--task", action="append", default=[],
                   help="Inline task description (repeatable).")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a checklist by ObjectId.")
    p.add_argument("--id", required=True)
    p.add_argument("--title")
    p.add_argument("--position", type=int)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a checklist by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("list", help="List checklists on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
```

- [ ] **Step 4: Wire `checklists.register(sub)` in entry script.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_checklists -v
```
Expected: 6 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/checklists.py tests/test_checklists.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add checklists group (create, update, delete, list)

## Problem
v1.4 exposes the full checklist lifecycle externally for the first time
(POST /checklists, PATCH/DELETE /checklists/{id}, GET /cards/{id}/checklists).
v2 had nothing.

## Solution
kz/checklists.py implements create/update/delete/list. create resolves --card
to ObjectId and accepts repeatable --task to seed inline tasks. update
patches title/position; delete uses the flat ObjectId URL; list uses the
card sub-resource.

## Verified
python3 -m unittest tests.test_checklists passes (6 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 16: Tasks module (`kz.tasks`)

**Endpoints:** `POST /tasks`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}`, `POST /tasks/{id}/move`. Subcommands: `create`, `update`, `delete`, `move`.

**Files:**
- Create: `scripts/kz/tasks.py`
- Create: `tests/test_tasks.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_tasks.py`.**

```python
import io
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import tasks as kz_tasks
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
                kz_tasks.cmd_create(_ns(
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
                kz_tasks.cmd_create(_ns(
                    checklist=CHK_ID, description="X",
                    position=0, due_at="2026-06-01T17:00:00.000Z",
                ), _Ctx())

    def test_update_completed(self):
        with FakeApi() as fake:
            fake.expect("PATCH", f"/tasks/{TASK_ID}", body={
                "completed": True,
            }).returns({"_id": TASK_ID, "completed": True})
            with patch("sys.stdout", io.StringIO()):
                kz_tasks.cmd_update(_ns(
                    id=TASK_ID, completed=True, description=None,
                    position=None, due_at=None,
                ), _Ctx())

    def test_delete(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/tasks/{TASK_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_tasks.cmd_delete(_ns(id=TASK_ID), _Ctx())

    def test_move_between_checklists(self):
        with FakeApi() as fake:
            fake.expect("POST", f"/tasks/{TASK_ID}/move", body={
                "checklistFrom": CHK_ID,
                "checklistTo": DEST_CHK,
                "position": 0,
            }).returns({"_id": TASK_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_tasks.cmd_move(_ns(
                    id=TASK_ID, checklist_from=CHK_ID,
                    checklist_to=DEST_CHK, position=0,
                ), _Ctx())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect ImportError.**

- [ ] **Step 3: Implement `scripts/kz/tasks.py`.**

```python
"""Tasks group: create, update, delete, move."""
from kz import http as kz_http
from kz import output as kz_output


def cmd_create(args, ctx):
    body = {"checklist": args.checklist, "description": args.description}
    if args.position is not None:
        body["position"] = args.position
    if args.due_at:
        body["dueAt"] = args.due_at
    resp = kz_http.api_request("POST", "/tasks", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.completed is not None:
        body["completed"] = bool(args.completed)
    if args.description is not None:
        body["description"] = args.description
    if args.position is not None:
        body["position"] = args.position
    if args.due_at is not None:
        body["dueAt"] = args.due_at
    if not body:
        raise ValueError("Provide one of --completed/--description/--position/--due-at")
    resp = kz_http.api_request("PATCH", f"/tasks/{args.id}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kz_http.api_request("DELETE", f"/tasks/{args.id}")
    kz_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_move(args, ctx):
    body = {
        "checklistFrom": args.checklist_from,
        "checklistTo": args.checklist_to,
        "position": args.position,
    }
    resp = kz_http.api_request("POST", f"/tasks/{args.id}/move", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("tasks", help="Tasks within a checklist.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("create", help="Add a task to a checklist.")
    p.add_argument("--checklist", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--position", type=int)
    p.add_argument("--due-at")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a task by ObjectId.")
    p.add_argument("--id", required=True)
    p.add_argument("--completed", type=lambda s: s.lower() == "true", default=None)
    p.add_argument("--description")
    p.add_argument("--position", type=int)
    p.add_argument("--due-at")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a task by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("move", help="Move a task between checklists or positions.")
    p.add_argument("--id", required=True)
    p.add_argument("--checklist-from", required=True)
    p.add_argument("--checklist-to", required=True)
    p.add_argument("--position", type=int, required=True)
    p.set_defaults(func=cmd_move)
```

- [ ] **Step 4: Wire `tasks.register(sub)` in entry script.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_tasks -v
```
Expected: 5 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/tasks.py tests/test_tasks.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add tasks group (create, update, delete, move)

## Problem
v1.4 exposes per-task lifecycle: POST /tasks, PATCH/DELETE /tasks/{id},
POST /tasks/{id}/move. Mark-as-done is a PATCH with {"completed": true}.

## Solution
kz/tasks.py implements create/update/delete/move. update accepts
--completed (bool), --description, --position, --due-at and includes only
fields the user actually passed. move requires both --checklist-from and
--checklist-to (canonical to support same-checklist reordering too).

## Verified
python3 -m unittest tests.test_tasks passes (5 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 17: Tokens module (`kz.tokens`)

**Endpoints:** `POST /tokens`, `DELETE /tokens/{id}`, `GET /cards/{id}/tokens`. Subcommands: `assign`, `revoke`, `list`.

**Files:**
- Create: `scripts/kz/tokens.py`
- Create: `tests/test_tokens.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_tokens.py`.**

```python
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
from kz import tokens as kz_tokens
from kz.cache import Cache
from tests.fakes import FakeApi


CARD_OID = "6700aabbccddeeff00112233"
CARDTOKEN_ID = "9999aaaa8888bbbb7777cccc"


class _Ctx:
    def __init__(self):
        self.board = "BOARD1"
        self.pretty = False
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(os.path.join(self._tmp.name, "c.json"))


def _ns(**kw):
    return type("N", (), kw)()


class TestTokens(unittest.TestCase):
    def test_assign(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("POST", "/tokens", body={
                "card": CARD_OID, "tokenId": "TKN1", "board": "BOARD1",
            }).returns({"_id": CARDTOKEN_ID})
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_assign(_ns(card="42", token_id="TKN1"), ctx)

    def test_revoke(self):
        with FakeApi() as fake:
            fake.expect("DELETE", f"/tokens/{CARDTOKEN_ID}").returns(None)
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_revoke(_ns(id=CARDTOKEN_ID), _Ctx())

    def test_list_uses_card_subresource(self):
        ctx = _Ctx()
        ctx.cache.set_card_mapping("BOARD1", 42, CARD_OID)
        with FakeApi() as fake:
            fake.expect("GET", f"/cards/{CARD_OID}/tokens").returns([])
            with patch("sys.stdout", io.StringIO()):
                kz_tokens.cmd_list(_ns(card="42"), ctx)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect ImportError.**

- [ ] **Step 3: Implement `scripts/kz/tokens.py`.**

```python
"""Tokens group: assign, revoke, list (card share tokens)."""
from kz import http as kz_http
from kz import ids as kz_ids
from kz import output as kz_output


def _resolve_card(ctx, value):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    return kz_ids.resolve_card_object_id(value, ctx.board, ctx.cache)


def cmd_assign(args, ctx):
    oid = _resolve_card(ctx, args.card)
    body = {"card": oid, "tokenId": args.token_id, "board": ctx.board}
    resp = kz_http.api_request("POST", "/tokens", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_revoke(args, ctx):
    kz_http.api_request("DELETE", f"/tokens/{args.id}")
    kz_output.print_json({"revoked": True, "id": args.id}, pretty=ctx.pretty)


def cmd_list(args, ctx):
    oid = _resolve_card(ctx, args.card)
    resp = kz_http.api_request("GET", f"/cards/{oid}/tokens")
    kz_output.print_json(resp, pretty=ctx.pretty)


def register(subparsers):
    g = subparsers.add_parser("tokens", help="Card share tokens.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    p = sub.add_parser("assign", help="Assign a token to a card.")
    p.add_argument("--card", required=True)
    p.add_argument("--token-id", required=True)
    p.set_defaults(func=cmd_assign)

    p = sub.add_parser("revoke", help="Revoke a card token by ObjectId.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_revoke)

    p = sub.add_parser("list", help="List tokens on a card.")
    p.add_argument("--card", required=True)
    p.set_defaults(func=cmd_list)
```

- [ ] **Step 4: Wire `tokens.register(sub)` in entry script.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_tokens -v
```
Expected: 3 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/tokens.py tests/test_tokens.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add tokens group (assign, revoke, list)

## Problem
v1.4 introduces card share tokens: POST /tokens (with card+tokenId+board
in body), DELETE /tokens/{id}, GET /cards/{id}/tokens.

## Solution
kz/tokens.py implements assign/revoke/list. assign resolves --card to
ObjectId and posts {card, tokenId, board}; revoke deletes by token
ObjectId; list uses the card sub-resource.

## Verified
python3 -m unittest tests.test_tokens passes (3 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 18: Webhooks module + signature verifier (`kz.webhooks`)

**Endpoints:** `GET /webhooks`, `GET /webhooks/{id}`, `POST /webhooks`, `PUT /webhooks/{id}`, `DELETE /webhooks/{id}`, `POST /webhooks/{id}/test`. Plus the offline `verify-signature` helper (HMAC-SHA1).

**Files:**
- Create: `scripts/kz/webhooks.py`
- Create: `tests/test_webhooks.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_webhooks.py`.**

```python
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
```

- [ ] **Step 2: Run — expect ImportError.**

- [ ] **Step 3: Implement `scripts/kz/webhooks.py`.**

```python
"""Webhooks group: list, get, create, update, delete, test, verify-signature."""
import hashlib
import hmac
import os

from kz import http as kz_http
from kz import output as kz_output


def cmd_list(args, ctx):
    resp = kz_http.api_request("GET", "/webhooks")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_get(args, ctx):
    resp = kz_http.api_request("GET", f"/webhooks/{args.id}")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_create(args, ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    body = {"board": ctx.board, "event": args.event, "url": args.url}
    resp = kz_http.api_request("POST", "/webhooks", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_update(args, ctx):
    body = {}
    if args.url is not None:
        body["url"] = args.url
    if args.event is not None:
        body["event"] = args.event
    if not body:
        raise ValueError("Provide --url or --event")
    resp = kz_http.api_request("PUT", f"/webhooks/{args.id}", body=body)
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_delete(args, ctx):
    kz_http.api_request("DELETE", f"/webhooks/{args.id}")
    kz_output.print_json({"deleted": True, "id": args.id}, pretty=ctx.pretty)


def cmd_test(args, ctx):
    resp = kz_http.api_request("POST", f"/webhooks/{args.id}/test")
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_verify_signature(args, ctx):
    key = args.webhook_key or os.environ.get("KZ_WEBHOOK_KEY")
    if not key:
        raise ValueError("Provide --webhook-key or set KZ_WEBHOOK_KEY")
    with open(args.payload_file, "rb") as f:
        payload = f.read()
    computed = hmac.new(key.encode("utf-8"), payload, hashlib.sha1).hexdigest()
    matched = hmac.compare_digest(computed, args.signature)
    kz_output.print_json({"verified": matched, "computed": computed},
                          pretty=ctx.pretty)
    return 0 if matched else 1


_EVENTS = ("CARD_CREATED", "CARD_MOVED", "CARD_UPDATED")


def register(subparsers):
    g = subparsers.add_parser("webhooks", help="Webhook CRUD + test + verify-signature.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True

    sub.add_parser("list", help="List webhooks for the active board.").set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="Get one webhook by id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("create", help="Register a webhook on the active board.")
    p.add_argument("--event", required=True, choices=_EVENTS)
    p.add_argument("--url", required=True)
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Update a webhook by id.")
    p.add_argument("--id", required=True)
    p.add_argument("--url")
    p.add_argument("--event", choices=_EVENTS)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete a webhook by id.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("test", help="Send a synthetic test event.")
    p.add_argument("--id", required=True)
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("verify-signature",
                       help="Verify an HMAC-SHA1 webhook signature locally.")
    p.add_argument("--webhook-key", help="Override KZ_WEBHOOK_KEY.")
    p.add_argument("--payload-file", required=True,
                   help="Bytes that were signed (notification.payload).")
    p.add_argument("--signature", required=True, help="X-KanbanZone-Signature value.")
    p.set_defaults(func=cmd_verify_signature)
```

- [ ] **Step 4: Wire `webhooks.register(sub)` in entry script.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_webhooks -v
```
Expected: 10 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/webhooks.py tests/test_webhooks.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add webhooks group (CRUD, test, verify-signature)

## Problem
v1.4 promotes webhook management from UI-only to full CRUD via API. The
docs flag HMAC-SHA1 signature verification as mandatory, so the skill
should expose a local helper to make it reachable from any agent.

## Solution
kz/webhooks.py implements list/get/create/update/delete/test against the
new /webhooks endpoints. create restricts --event to {CARD_CREATED,
CARD_MOVED, CARD_UPDATED}. cmd_verify_signature is fully offline: reads
the key from --webhook-key or KZ_WEBHOOK_KEY, signs the payload bytes
with HMAC-SHA1, compares constant-time against --signature, prints
{verified, computed}, exits 0 on match / 1 on mismatch.

## Verified
python3 -m unittest tests.test_webhooks passes (10 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 19: Reports module (`kz.reports`)

**Endpoints:** 8 of `GET /boards/{publicId}/reports/{reportType}`. Subcommands: `throughput`, `arrival-rate`, `cycle-time`, `lead-time`, `flow`, `flow-efficiency`, `allocation`, `abandoned-effort`. Each is a thin wrapper over a shared `_run_report` helper.

**Files:**
- Create: `scripts/kz/reports.py`
- Create: `tests/test_reports.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_reports.py`.**

```python
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
```

- [ ] **Step 2: Run — expect ImportError.**

- [ ] **Step 3: Implement `scripts/kz/reports.py`.**

```python
"""Reports group: 8 report types, all GET /boards/{publicId}/reports/{type}."""
from kz import http as kz_http
from kz import output as kz_output


def _run_report(report_type, args, ctx):
    if not ctx.board:
        raise ValueError("--board or KANBAN_ZONE_BOARD_ID is required")
    params = {}
    if args.from_date:
        params["from"] = args.from_date
    if args.to_date:
        params["to"] = args.to_date
    resp = kz_http.api_request(
        "GET", f"/boards/{ctx.board}/reports/{report_type}",
        params=params or None,
    )
    kz_output.print_json(resp, pretty=ctx.pretty)


def cmd_throughput(args, ctx): _run_report("throughput", args, ctx)
def cmd_arrival_rate(args, ctx): _run_report("arrival-rate", args, ctx)
def cmd_cycle_time(args, ctx): _run_report("cycle-time", args, ctx)
def cmd_lead_time(args, ctx): _run_report("lead-time", args, ctx)
def cmd_flow(args, ctx): _run_report("flow", args, ctx)
def cmd_flow_efficiency(args, ctx): _run_report("flow-efficiency", args, ctx)
def cmd_allocation(args, ctx): _run_report("allocation", args, ctx)
def cmd_abandoned_effort(args, ctx): _run_report("abandoned-effort", args, ctx)


_REPORTS = [
    ("throughput", cmd_throughput),
    ("arrival-rate", cmd_arrival_rate),
    ("cycle-time", cmd_cycle_time),
    ("lead-time", cmd_lead_time),
    ("flow", cmd_flow),
    ("flow-efficiency", cmd_flow_efficiency),
    ("allocation", cmd_allocation),
    ("abandoned-effort", cmd_abandoned_effort),
]


def register(subparsers):
    g = subparsers.add_parser("reports", help="Board-level analytics reports.")
    sub = g.add_subparsers(dest="subcommand")
    sub.required = True
    for slug, handler in _REPORTS:
        p = sub.add_parser(slug, help=f"{slug} report")
        p.add_argument("--from-date", help="ISO date (e.g. 2026-01-01)")
        p.add_argument("--to-date", help="ISO date (e.g. 2026-04-01)")
        p.set_defaults(func=handler)
```

- [ ] **Step 4: Wire `reports.register(sub)` in entry script.**

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_reports -v
```
Expected: 2 tests PASS (subTest counts as one for unittest's pass count, but all 8 report types run).

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/reports.py tests/test_reports.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add reports group (8 report types)

## Problem
v1.4 exposes 8 board-level analytics reports under
/boards/{publicId}/reports/{type}; v2 had none.

## Solution
kz/reports.py defines a shared _run_report helper and 8 thin wrappers
(throughput, arrival-rate, cycle-time, lead-time, flow, flow-efficiency,
allocation, abandoned-effort). Each wrapper has its own --help and
--from-date/--to-date flags. Subparsers are wired from a (slug, handler)
table for one-line addition of future report types.

## Verified
python3 -m unittest tests.test_reports passes (covers all 8 via subTest).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Legacy aliases + integration

### Task 20: Legacy aliases module (`kz.legacy`)

**Goal:** Keep all 12 v2 flat commands working but suppressed from `--help`. Each alias dispatches to the matching grouped handler with the equivalent argparse `Namespace`.

**Files:**
- Create: `scripts/kz/legacy.py`
- Create: `tests/test_legacy_aliases.py`
- Modify: `scripts/kanban_zone_api.py`

- [ ] **Step 1: Write failing tests `tests/test_legacy_aliases.py`.**

```python
import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")


def help_text(*args):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    r = subprocess.run([sys.executable, SCRIPT, *args, "--help"],
                        env=env, capture_output=True, text=True)
    return (r.stdout + r.stderr).lower()


LEGACY_COMMANDS = [
    "boards", "board", "cards", "card", "create-card", "create-cards",
    "update-card", "move-card", "link-card", "unlink-card", "search-cards",
    "wip-check",
]


class TestLegacyAliases(unittest.TestCase):
    def test_root_help_does_not_show_legacy_commands(self):
        text = help_text()
        for cmd in LEGACY_COMMANDS:
            self.assertNotIn(f" {cmd}\n", text + "\n",
                f"legacy alias {cmd!r} appeared in root --help")

    def test_each_legacy_command_has_its_own_help(self):
        # legacy commands suppressed from list, but invokable
        env = dict(os.environ)
        env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
        for cmd in LEGACY_COMMANDS:
            r = subprocess.run([sys.executable, SCRIPT, cmd, "--help"],
                                env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0,
                f"legacy {cmd} --help failed: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect failure (some legacy aliases not yet wired).**

```bash
python3 -m unittest tests.test_legacy_aliases -v
```

- [ ] **Step 3: Implement `scripts/kz/legacy.py`.** Each alias is a top-level subparser registered with `help=argparse.SUPPRESS`; its handler builds a fresh `Namespace` matching what the grouped handler expects.

```python
"""Hidden v2 flat-command aliases. Suppressed from --help, kept for back-compat.

Each alias mirrors the v2 CLI surface and dispatches to the equivalent v3
grouped handler so existing scripts keep working without code changes.
"""
import argparse

from kz import boards as kz_boards
from kz import cards as kz_cards


def _add(sub, name, callback, configure=lambda p: None):
    p = sub.add_parser(name, help=argparse.SUPPRESS)
    configure(p)
    p.set_defaults(func=callback)
    return p


def _wrap_boards_list(args, ctx):
    args.include_archived = getattr(args, "include_archived", False)
    args.include_columns = getattr(args, "include_columns", False)
    return kz_boards.cmd_list(args, ctx)


def _wrap_boards_get(args, ctx):
    args.include_columns = getattr(args, "include_columns", False)
    args.include_members = False
    args.include_labels = False
    args.include_custom_fields = False
    return kz_boards.cmd_get(args, ctx)


def _wrap_cards_list(args, ctx):
    args.page = getattr(args, "page", 1)
    args.count = getattr(args, "count", 100)
    args.include_archived = getattr(args, "include_archived", False)
    args.days_since_last_update = getattr(args, "days_since_last_update", None)
    for k in ("label", "owner", "column", "priority", "query"):
        setattr(args, k, getattr(args, k, None))
    args.blocked = getattr(args, "blocked", False)
    return kz_cards.cmd_list(args, ctx)


def _wrap_cards_get(args, ctx):
    args.id = args.number  # v2 used --number
    return kz_cards.cmd_get(args, ctx)


def _wrap_cards_create(args, ctx):
    return kz_cards.cmd_create(args, ctx)


def _wrap_cards_create_bulk(args, ctx):
    return kz_cards.cmd_create_bulk(args, ctx)


def _wrap_cards_update(args, ctx):
    args.id = str(args.id)  # accepts number-as-int from v2
    return kz_cards.cmd_update(args, ctx)


def _wrap_cards_move(args, ctx):
    args.id = str(args.id)
    args.add_to_top = getattr(args, "add_to_top", False)
    return kz_cards.cmd_move(args, ctx)


def _wrap_cards_links_add(args, ctx):
    args.id = str(args.id)
    return kz_cards.cmd_links_add(args, ctx)


def _wrap_cards_links_remove(args, ctx):
    args.id = str(args.id)
    return kz_cards.cmd_links_remove(args, ctx)


def _wrap_cards_search(args, ctx):
    return kz_cards.cmd_search(args, ctx)


def _wrap_cards_wip_check(args, ctx):
    return kz_cards.cmd_wip_check(args, ctx)


def register(subparsers):
    # boards / board
    _add(subparsers, "boards", _wrap_boards_list, lambda p: (
        p.add_argument("--include-archived", action="store_true"),
        p.add_argument("--include-columns", action="store_true"),
    ))
    _add(subparsers, "board", _wrap_boards_get, lambda p: (
        p.add_argument("--include-columns", action="store_true"),
    ))

    # cards / card
    _add(subparsers, "cards", _wrap_cards_list, lambda p: (
        p.add_argument("--page", type=int, default=1),
        p.add_argument("--count", type=int, default=100),
        p.add_argument("--include-archived", action="store_true"),
        p.add_argument("--days-since-last-update", type=int, default=None),
        p.add_argument("--label"),
        p.add_argument("--owner"),
        p.add_argument("--column"),
        p.add_argument("--priority"),
        p.add_argument("--blocked", action="store_true"),
        p.add_argument("--query"),
    ))
    _add(subparsers, "card", _wrap_cards_get, lambda p: (
        p.add_argument("--number", required=True),
    ))

    # create-card / create-cards
    _add(subparsers, "create-card", _wrap_cards_create, lambda p: (
        p.add_argument("--title", required=True),
        p.add_argument("--description"),
        p.add_argument("--description-file"),
        p.add_argument("--column-id"),
        p.add_argument("--owner"),
        p.add_argument("--priority"),
        p.add_argument("--label"),
        p.add_argument("--size"),
        p.add_argument("--due-at"),
        p.add_argument("--blocked", action="store_true"),
        p.add_argument("--blocked-reason"),
        p.add_argument("--add-to-top", action="store_true"),
        p.add_argument("--watcher", action="append", default=[]),
        p.add_argument("--custom-field", action="append", default=[]),
        p.add_argument("--template-id"),
    ))
    _add(subparsers, "create-cards", _wrap_cards_create_bulk, lambda p: (
        p.add_argument("--file", required=True),
    ))

    # update-card / move-card
    _add(subparsers, "update-card", _wrap_cards_update, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--title"),
        p.add_argument("--description"),
        p.add_argument("--description-file"),
        p.add_argument("--owner"),
        p.add_argument("--priority"),
        p.add_argument("--label"),
        p.add_argument("--size"),
        p.add_argument("--due-at"),
        p.add_argument("--blocked", type=lambda s: s.lower() == "true", default=None),
        p.add_argument("--blocked-reason"),
        p.add_argument("--watcher", action="append", default=[]),
        p.add_argument("--custom-field", action="append", default=[]),
    ))
    _add(subparsers, "move-card", _wrap_cards_move, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--column-id", required=True),
        p.add_argument("--add-to-top", action="store_true"),
    ))

    # link-card / unlink-card
    _add(subparsers, "link-card", _wrap_cards_links_add, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--card", type=int),
        p.add_argument("--url"),
        p.add_argument("--title"),
        p.add_argument("--type", default=None),
    ))
    _add(subparsers, "unlink-card", _wrap_cards_links_remove, lambda p: (
        p.add_argument("--id", required=True),
        p.add_argument("--card", type=int),
        p.add_argument("--url"),
    ))

    # search-cards / wip-check
    _add(subparsers, "search-cards", _wrap_cards_search, lambda p: (
        p.add_argument("--query"),
        p.add_argument("--label"),
        p.add_argument("--owner"),
    ))
    _add(subparsers, "wip-check", _wrap_cards_wip_check, lambda p: None)
```

- [ ] **Step 4: Wire `legacy.register(sub)` LAST in the entry script** (so legacy aliases are added after grouped commands but their `help=SUPPRESS` keeps them out of root help).

- [ ] **Step 5: Run — expect pass.**

```bash
python3 -m unittest tests.test_legacy_aliases -v
```
Expected: 2 tests PASS.

- [ ] **Step 6: Commit.**

```bash
git add scripts/kz/legacy.py tests/test_legacy_aliases.py scripts/kanban_zone_api.py
git commit -m "$(cat <<'EOF'
Add hidden v2 back-compat aliases

## Problem
v3 reorganises the CLI into resource groups, which breaks every script
that calls the v2 flat commands. Per the v3 design, all 12 flat commands
must keep working but stay out of --help to encourage migration.

## Solution
kz/legacy.py registers each v2 flat command as a top-level subparser with
help=argparse.SUPPRESS. Each alias's handler reshapes the legacy argparse
Namespace into the grouped handler's expected shape and dispatches.
Tests assert: (a) root --help does not list any legacy command; (b) each
legacy command still has its own --help.

## Verified
python3 -m unittest tests.test_legacy_aliases passes (2 tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 21: Integration smoke test (`test_cli_help`)

Already created the skeleton in Task 8. Now extend it to assert the full grouped surface is present.

**Files:**
- Modify: `tests/test_cli_skeleton.py` (rename to `tests/test_cli_help.py` for clarity)

- [ ] **Step 1: Move and extend.**

```bash
git mv tests/test_cli_skeleton.py tests/test_cli_help.py
```

Replace the file contents with:

```python
import os
import subprocess
import sys
import unittest


SCRIPT = os.path.join("scripts", "kanban_zone_api.py")
GROUPS_AND_SUBCOMMANDS = {
    "boards": ["list", "get", "columns", "labels", "members",
                "custom-fields", "templates"],
    "cards": ["list", "get", "create", "create-bulk", "update", "move",
              "delete", "history", "metrics", "links-add", "links-remove",
              "search", "wip-check"],
    "comments": ["add", "list"],
    "checklists": ["create", "update", "delete", "list"],
    "tasks": ["create", "update", "delete", "move"],
    "webhooks": ["list", "get", "create", "update", "delete", "test",
                 "verify-signature"],
    "reports": ["throughput", "arrival-rate", "cycle-time", "lead-time",
                "flow", "flow-efficiency", "allocation", "abandoned-effort"],
    "tokens": ["assign", "revoke", "list"],
    "org": ["me", "context"],
}


def run(*args):
    env = dict(os.environ)
    env.setdefault("KANBAN_ZONE_API_KEY", "test:key")
    return subprocess.run([sys.executable, SCRIPT, *args], env=env,
                            capture_output=True, text=True)


class TestRootHelp(unittest.TestCase):
    def test_each_group_appears(self):
        out = run("--help").stdout
        for group in GROUPS_AND_SUBCOMMANDS:
            self.assertIn(group, out)

    def test_global_flags(self):
        out = run("--help").stdout
        for flag in ["--board", "--no-cache", "--pretty", "--api-token"]:
            self.assertIn(flag, out)


class TestGroupHelp(unittest.TestCase):
    def test_each_group_lists_its_subcommands(self):
        for group, subs in GROUPS_AND_SUBCOMMANDS.items():
            with self.subTest(group=group):
                out = run(group, "--help").stdout
                for sub in subs:
                    self.assertIn(sub, out, f"{group}: missing {sub}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect pass.**

```bash
python3 -m unittest tests.test_cli_help -v
```
Expected: 3 tests PASS (subTest count for groups separately).

- [ ] **Step 3: Commit.**

```bash
git add tests/test_cli_help.py
git commit -m "$(cat <<'EOF'
Add integration help test covering the full grouped surface

## Problem
The full v3 CLI must present every grouped command in --help and every
subcommand in its group --help. Without an integration smoke test, a
forgotten register() call could ship silently.

## Solution
tests/test_cli_help.py runs the entry script as a subprocess and asserts
each group appears in root --help, each global flag is present, and each
group's --help lists every documented subcommand.

## Verified
python3 -m unittest tests.test_cli_help passes (covers all 9 groups).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 4 — Documentation

The doc tasks are largely "write this file." They have no test step (markdown is not unit-tested) but each commit verifies the file renders cleanly via `python3 -m mistune`-equivalent (we'll just visually verify or use `python3 -c "import markdown"` if it's installed; otherwise simple file existence + line count check).

### Task 22: Rewrite `SKILL.md`

**Files:**
- Modify: `SKILL.md` (full rewrite)

- [ ] **Step 1: Replace `SKILL.md` with the v3 agent-facing content.**

Use this skeleton (frontmatter version stays at "2.1.0" until Task 28):

```markdown
---
name: kanban-zone
description: Interact with Kanban Zone kanban boards via the Kanban Zone API. Use when the user wants to manage kanban cards, boards, comments, checklists, tasks, webhooks, or board reports. Even if the user just says "check the board", "what's in progress", or mentions kanban cards, use this skill.
license: MIT
compatibility: Requires python3 and environment variables KANBAN_ZONE_API_KEY and KANBAN_ZONE_BOARD_ID. Wraps Kanban Zone Public API v1.4.
metadata:
  version: "2.1.0"
  openclaw:
    requires:
      env:
        - KANBAN_ZONE_API_KEY
        - KANBAN_ZONE_BOARD_ID
      bins:
        - python3
    primaryEnv: KANBAN_ZONE_API_KEY
    homepage: https://docs.kanbanzone.io
---

# Kanban Zone

Manage Kanban Zone kanban boards through the Kanban Zone Public API (v1.4).

## ⚠️ Exec Safety Rule — Multi-line Commands

(Keep verbatim from v2 — see existing SKILL.md.)

## Environment Setup

(Keep verbatim from v2.)

## Quick Start

```bash
python3 scripts/kanban_zone_api.py boards list
python3 scripts/kanban_zone_api.py boards get
python3 scripts/kanban_zone_api.py cards list --label "Bug"
python3 scripts/kanban_zone_api.py cards get --id 42
python3 scripts/kanban_zone_api.py cards create --title "New task" --column-id COL1
python3 scripts/kanban_zone_api.py cards move --id 42 --column-id COL2
python3 scripts/kanban_zone_api.py cards delete --id 42
python3 scripts/kanban_zone_api.py comments add --card 42 --text "..."
python3 scripts/kanban_zone_api.py checklists create --card 42 --title "QA" --task "T1"
python3 scripts/kanban_zone_api.py reports throughput --from-date 2026-01-01 --to-date 2026-04-01
```

## Resource Groups

(One section per group: boards, cards, comments, checklists, tasks, webhooks,
 reports, tokens, org. Each section: 2-3 example invocations + a one-line
 description of every subcommand. Use the GROUPS_AND_SUBCOMMANDS table from
 tests/test_cli_help.py as the canonical list.)

## Description Updates (IMPORTANT)

(Keep verbatim from v2: --description-file, HTML only, no `<table>`, use `<pre>`.)

## Card ID Auto-Detection

`--id` accepts either a card number (digits) or a 24-hex ObjectId. The skill
auto-detects which kind and resolves through the bidirectional cache before
calling ObjectId-keyed endpoints. Sub-resource IDs (checklist/task/comment/
token/webhook) are always 24-hex ObjectIds.

## Cache (with bidirectional ID mapping)

(Keep v2 cache section, add the new section explaining the byNumber/byObjectId
 schema and that the cache is opportunistically populated by every list/get
 response.)

## Column States

(Keep verbatim from v2.)

## Script Reference

(Replace the v2 table with a grouped table listing every group/subcommand and
 its one-line description. Mirror tests/test_cli_help.py's
 GROUPS_AND_SUBCOMMANDS for completeness.)

## Migration from v2

If you previously used flat commands (`create-card`, `update-card`, ...), they
still work as hidden aliases — see `references/migration-from-v2.md` for the
full mapping. New code should use the grouped commands documented above.

## API Reference

See [references/api-reference.md](./references/api-reference.md).
```

The above is the structure — the engineer fills in the prose for each section using:
- Existing v2 SKILL.md as the source for sections marked "(Keep verbatim from v2.)".
- The `GROUPS_AND_SUBCOMMANDS` dict from `tests/test_cli_help.py` as the canonical command list.
- The Quick Start examples above as the cookbook seed.

- [ ] **Step 2: Verify the file is well-formed Markdown (basic line count + headers present).**

```bash
test "$(grep -c '^## ' SKILL.md)" -ge 9
```

- [ ] **Step 3: Commit.**

```bash
git add SKILL.md
git commit -m "$(cat <<'EOF'
Rewrite SKILL.md for v3 grouped command surface

## Problem
SKILL.md still documents the v2 flat surface and API v1.3. Agents loading
the skill see the wrong command names and miss every new resource group.

## Solution
Full rewrite. Frontmatter description widened to mention comments,
checklists, tasks, webhooks, reports. New "Resource Groups" section with
one block per group. Cache section updated for bidirectional ID mapping.
Card ID auto-detection rule documented. Existing exec-safety / description
formatting / column-states sections preserved verbatim. Frontmatter
version stays at 2.1.0; bumped to 3.0.0 in Task 28.

## Verified
SKILL.md has nine or more `## ` headers; renders in any Markdown viewer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 23: Rewrite `README.md`

**Files:**
- Modify: `README.md` (full rewrite)

- [ ] **Step 1: Replace README.md with the v3 published-face content.**

Required sections (engineer writes the prose; structure is fixed):

1. **What it is** — one-paragraph pitch: stdlib Python 3 skill that wraps Kanban Zone Public API v1.4 from any Claude-Code-compatible workspace; built in partnership with Kanban Zone.
2. **Install** — clone or `claude plugin add` directions; minimum Python version (3.8+); env setup (`.env` with `KANBAN_ZONE_API_KEY` and `KANBAN_ZONE_BOARD_ID`).
3. **API key** — how to generate it from Kanban Zone Settings → Integrations → API Key.
4. **Cookbook** — 8-10 worked examples demonstrating real flows. Suggested:
   - List boards and pick one to work on
   - Create a card with watchers and custom fields
   - Update the description from a temp file
   - Move a card to "In Progress"
   - Add a comment to a card
   - Create a checklist with inline tasks; mark a task complete
   - Register a webhook and verify a delivery's signature
   - Pull a throughput report for the last quarter
   - Audit overdue cards across all boards via cards search
   - Bulk-create cards from a JSON file
5. **Command reference** — link to SKILL.md for the full surface.
6. **What's new in v3** — bullet list pulled from CHANGELOG.md (one line each), then a link to CHANGELOG.md.
7. **Migration from v2** — one-paragraph summary + link to references/migration-from-v2.md.
8. **License** — MIT, link to LICENSE.txt.
9. **Acknowledgements** — built in partnership with Kanban Zone.

- [ ] **Step 2: Sanity-check section count.**

```bash
test "$(grep -c '^## ' README.md)" -ge 9
```

- [ ] **Step 3: Commit.**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
Rewrite README.md as v3 published face

## Problem
README still describes the v2 flat surface and v1.3 API. As the published
face of an officially partnered skill, it needs a polished cookbook and
clear migration story.

## Solution
Full rewrite with nine sections: pitch, install, API key, 10-flow cookbook,
command reference link, "what's new in v3", migration paragraph, license,
acknowledgements. Cookbook covers the full lifecycle (create, comment,
checklist, webhook with signature verify, report).

## Verified
README has nine or more `## ` headers; renders in GitHub.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 24: Rewrite `AGENTS.md`

**Files:**
- Modify: `AGENTS.md` (full rewrite)

- [ ] **Step 1: Replace AGENTS.md with contributor guide.**

Required sections:

1. **Sync clause (PROMINENT, top of file).** Verbatim:
   > **CLAUDE.md / AGENTS.md sync:** if both files exist in this repo, they MUST be identical and updated together in the same commit. SKILL.md and AGENTS.md are NOT required to be identical — SKILL.md is agent-facing, AGENTS.md is contributor-facing.
2. **Project layout.** Tree of `scripts/kz/`, what each module owns, where tests live, where fixtures live.
3. **Add a new endpoint (template).** Step-by-step:
   - Add fixture in `tests/fixtures/`
   - Write failing test in `tests/test_<resource>.py`
   - Implement handler + register subparser in `scripts/kz/<resource>.py`
   - Run `python3 -m unittest tests.test_<resource>`
   - Run `make coverage` — must remain ≥ 95 %
   - Update `tests/test_cli_help.py` GROUPS_AND_SUBCOMMANDS
   - Commit per platform style
4. **Test commands.** `make test`, `make coverage`, `make coverage-html`, `make lint`.
5. **Coverage requirement.** ≥ 95 %; PRs that drop below this must add tests, not lower the threshold.
6. **Commit style.** Reference platform CLAUDE.md (this skill repo's parent platform conventions): subject ≤72 chars, body uses `## Problem` / `## Solution` / `## Verified`, KZ card link if applicable, `Co-Authored-By` trailer.
7. **No multi-line shell commands.** Use temp files for description bodies and inline scripts (existing v2 rule, preserved).

- [ ] **Step 2: Verify section count.**

```bash
test "$(grep -c '^## ' AGENTS.md)" -ge 7
```

- [ ] **Step 3: Commit.**

```bash
git add AGENTS.md
git commit -m "$(cat <<'EOF'
Rewrite AGENTS.md for v3 contributor workflow

## Problem
AGENTS.md still describes the v2 monolithic script. v3 splits into a
kz/ package with per-resource modules and a 95% coverage requirement;
contributors need to know where to put new code, how to test it, and
what commit style to follow.

## Solution
Full rewrite with seven sections: sync clause, project layout, add-an-
endpoint template, test commands, coverage requirement, commit style,
multi-line shell rule. The add-an-endpoint section walks through fixture
-> test -> handler -> register -> verify in order so the loop is muscle
memory.

## Verified
AGENTS.md has seven or more `## ` headers.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 25: Rewrite `references/api-reference.md`

**Files:**
- Modify: `references/api-reference.md` (full rewrite)

- [ ] **Step 1: Replace with the full v1.4 reference.** Source material:
- Postman collection at `https://docs.kanbanzone.io/kanbanzone-postman-collection.json` (downloaded during brainstorming; provides request body shapes).
- The grouped endpoint inventory in the design spec at `docs/superpowers/specs/2026-05-10-kanban-zone-skill-v3-design.md` §3.2.
- Live SPA scrape if needed for any endpoint not covered by Postman (use the Playwright snippet in the brainstorming transcript or call the API directly).

Required structure:

1. **Header.** "Kanban Zone Public API Reference (v1.4)", base URL `https://integrations.kanbanzone.io/v1/`, HTTPS only.
2. **Authentication.** Basic auth with base64-encoded `accessId:apiKey`. Optional `?api_token=...` query param.
3. **Rate limits.** Per-plan table.
4. **Per-resource sections,** in this order: Boards, Cards, Comments, Checklists, Tasks, Tokens, Webhooks, Reports, Templates, Organization.
5. **For each endpoint:** method + path, parameter table (with `In | Required | Type | Default | Description`), request body schema if any, response model name, notes.
6. **Data models.** All input and output models referenced above (`CardItemInputModel`, `CardItemOutputModel`, `ChecklistModel`, `TaskModel`, `CommentInput`, `WebhookInputModel`, `WebhookOutputModel`, etc.). Field tables.
7. **Webhook events + signature verification.** Events list (`CARD_CREATED`, `CARD_MOVED`, `CARD_UPDATED`); HMAC-SHA1 over `notification.payload`; `X-KanbanZone-Signature` header.
8. **Deprecated endpoints.** Table of deprecated paths and their canonical replacements.
9. **Column states.** Backlog / To Do / Buffer / In Progress / Done / Archive / None.
10. **Pagination.** `page`, `count` (max 100), `hasMore`, `totalAvailable`.

- [ ] **Step 2: Sanity check.**

```bash
test "$(grep -c '^## ' references/api-reference.md)" -ge 10
test "$(grep -c '^### ' references/api-reference.md)" -ge 30
```

- [ ] **Step 3: Commit.**

```bash
git add references/api-reference.md
git commit -m "$(cat <<'EOF'
Rewrite references/api-reference.md for API v1.4

## Problem
The reference still documents v1.3 only and is missing comments,
checklists, tasks, tokens, webhooks CRUD, reports, /me, /organization,
/templates, and the new flat /cards/{id} URLs.

## Solution
Full rewrite covering every v1.4 endpoint with parameter tables, request
body schemas, response model names, deprecated-endpoint mapping, webhook
event list, HMAC-SHA1 signature verification, column-state vocabulary,
and pagination semantics. Sourced from the official Postman collection
and the live Developer Docs SPA.

## Verified
The reference has at least 10 top-level sections and at least 30
endpoint subsections.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 26: Write `references/migration-from-v2.md`

**Files:**
- Create: `references/migration-from-v2.md`

- [ ] **Step 1: Write the migration doc.**

```markdown
# Migrating from Kanban Zone Skill v2 to v3

v3 reorganises the CLI into resource groups (`boards`, `cards`, `comments`,
...) and migrates wire calls to v1.4 canonical endpoints. **All v2 commands
keep working** as hidden aliases for back-compat.

## Hidden flat-command alias map

| v2 flat command   | v3 grouped equivalent      |
|-------------------|----------------------------|
| `boards`          | `boards list`              |
| `board`           | `boards get`               |
| `cards`           | `cards list`               |
| `card --number N` | `cards get --id N`         |
| `create-card`     | `cards create`             |
| `create-cards`    | `cards create-bulk`        |
| `update-card`     | `cards update`             |
| `move-card`       | `cards move`               |
| `link-card`       | `cards links-add`          |
| `unlink-card`     | `cards links-remove`       |
| `search-cards`    | `cards search`             |
| `wip-check`       | `cards wip-check`          |

## Silent endpoint migration

| v2 wire call (deprecated)        | v3 wire call (canonical)             |
|----------------------------------|--------------------------------------|
| `PUT /card/{id}`                 | `PATCH /cards/{id}`                  |
| `POST /cards/{id}/checklists`    | `POST /checklists`                   |
| `POST /cards/{id}/comments`      | `POST /comments`                     |
| `POST /cards/{id}/tokens`        | `POST /tokens`                       |
| `GET /board/{board}`             | `GET /boards/{publicId}`             |

The legacy aliases above call the new endpoints transparently. Output JSON
shape is unchanged; only the wire path differs.

## Cache schema migration

v2 cache files persist as-is. New keys (`cards.byNumber`, `cards.byObjectId`)
are added on first write that produces them. Nothing to do manually.

## When to update your scripts

You don't have to. Aliases will keep working. But:
- New code should use the grouped surface (it's the only thing in `--help`).
- New endpoints (comments, checklists, tasks, webhooks CRUD, reports, etc.)
  are only available through the grouped surface.

## When the aliases will go away

No deprecation date is currently set. The aliases will stay as long as Kanban
Zone Public API v1.4 honours its deprecated paths.
```

- [ ] **Step 2: Commit.**

```bash
git add references/migration-from-v2.md
git commit -m "$(cat <<'EOF'
Add references/migration-from-v2.md

## Problem
v3 introduces a grouped CLI and silent wire-level migration. Existing
users need a single doc that maps v2 commands to v3 commands, lists the
deprecated wire calls being migrated, and explains the cache forward-
compat story.

## Solution
references/migration-from-v2.md ships three tables (alias map, endpoint
map, cache notes) plus guidance on when to update scripts and when the
aliases will go away.

## Verified
File renders cleanly; tables are well-formed.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 27: Write `CHANGELOG.md`

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write the CHANGELOG.**

```markdown
# Changelog

All notable changes to the Kanban Zone skill. Versioning follows SemVer.

## [3.0.0] — 2026-05-DD

### Added
- Full coverage of Kanban Zone Public API v1.4: comments, checklists,
  tasks, card share tokens, webhook CRUD + signature verification, eight
  board reports, organization context, card history/metrics, board
  sub-resources (labels, members, custom fields, templates), card delete.
- Grouped CLI surface (`boards`, `cards`, `comments`, `checklists`,
  `tasks`, `webhooks`, `reports`, `tokens`, `org`).
- Bidirectional card-number ↔ ObjectId cache.
- Card ID auto-detection (`--id 42` or `--id 6700aabb...`).
- Offline `webhooks verify-signature` HMAC-SHA1 helper.
- `--no-cache`, `--pretty`, `--api-token`, `--board` global flags.
- Stdlib `unittest` test suite at ≥ 95 % line coverage.
- `Makefile` with `test`, `coverage`, `coverage-html`, `lint`, `clean`.
- `references/migration-from-v2.md`.

### Changed
- Restructured `scripts/kanban_zone_api.py` from monolith to entry script
  + `scripts/kz/` package with one module per resource.
- Wire calls migrated silently to v1.4 canonical paths
  (`PATCH /cards/{id}`, `POST /checklists`, `POST /comments`,
  `POST /tokens`, `GET /boards/{publicId}`). Deprecated v1.3 paths no
  longer used.
- `User-Agent` header now `kanban-zone-skill/3.0.0`.

### Deprecated
- v2 flat commands (`create-card`, `update-card`, `move-card`,
  `link-card`, `unlink-card`, `search-cards`, `wip-check`, `boards`,
  `board`, `cards`, `card`, `create-cards`) remain as hidden aliases
  but are not shown in `--help`. Use the grouped equivalents documented
  in `references/migration-from-v2.md`.

### Notes
- Cache file is forward-compatible — v2 cache files load cleanly.
- `.env` keys (`KANBAN_ZONE_API_KEY`, `KANBAN_ZONE_BOARD_ID`) unchanged.

## [2.1.0] — 2025-XX-XX
- HTML table warning added to description-formatting rules. (See git history.)

## [2.0.0] — 2025-XX-XX
- Rebrand from prior naming to "Kanban Zone"; env vars renamed. (See git history.)
```

The `2025-XX-XX` placeholders are reconstructed best-effort from `git log` — fill from `git log --format=%aI -- SKILL.md` for the rebrand commits.

- [ ] **Step 2: Commit.**

```bash
git add CHANGELOG.md
git commit -m "$(cat <<'EOF'
Add CHANGELOG.md starting at v3.0.0

## Problem
The repo has no CHANGELOG. As an officially published skill, version-to-
version changes need to be discoverable without trawling git log.

## Solution
CHANGELOG.md following Keep-a-Changelog style. v3.0.0 entry enumerates
Added/Changed/Deprecated/Notes; older versions reconstructed best-effort
from git history.

## Verified
File renders; v3.0.0 entry is the most recent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 28: Bump SKILL.md frontmatter version to 3.0.0

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Edit `SKILL.md` frontmatter.** Change `metadata.version: "2.1.0"` to `metadata.version: "3.0.0"`. Update the `compatibility:` line if it doesn't already mention v1.4.

- [ ] **Step 2: Verify.**

```bash
grep -n 'version: "3.0.0"' SKILL.md
```
Expected: one match in the frontmatter.

- [ ] **Step 3: Commit.**

```bash
git add SKILL.md
git commit -m "$(cat <<'EOF'
Bump skill version to 3.0.0

## Problem
Frontmatter version still shows 2.1.0 even though the surface, API
coverage, and command structure are all v3. Keeping the version label
honest is part of the SOC 2 evidence chain (CLAUDE.md == policy, version
stamps must match content).

## Solution
metadata.version: "3.0.0" in SKILL.md frontmatter. All other v3 changes
were committed in prior tasks; this is the explicit cutover.

## Verified
grep returns the updated version line.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 5 — Coverage gate

### Task 29: Run full coverage and close gaps to ≥95 %

**Files:**
- Possibly: any `tests/test_*.py` that needs more cases.

- [ ] **Step 1: Run full coverage.**

```bash
coverage run -m unittest discover tests
coverage report -m --fail-under=95
```

- [ ] **Step 2: If `--fail-under=95` fails, run an HTML report to find gaps.**

```bash
make coverage-html
open htmlcov/index.html  # macOS; on Linux: xdg-open
```

- [ ] **Step 3: Add tests for any uncovered branches.** Common gaps:
- Error paths in `kz/http.py` (URL error, JSON decode error).
- The `--no-cache` branch in `Cache.flush`.
- `_filter_cards` with multiple filters combined.
- The `register` legacy aliases for `link-card --url` (URL branch separate from card branch).
- `verify-signature` with `--webhook-key` *and* `KZ_WEBHOOK_KEY` set (precedence test).

For each gap, write the test in the matching `tests/test_*.py`, run the file, then re-run `coverage report --fail-under=95`.

- [ ] **Step 4: Final coverage check passes.**

```bash
coverage run -m unittest discover tests
coverage report --fail-under=95
```
Expected: `TOTAL` line shows ≥95 %, exit 0.

- [ ] **Step 5: Commit any added tests.**

```bash
git add tests/
git commit -m "$(cat <<'EOF'
Close coverage gaps to >=95%

## Problem
Initial test pass left a few uncovered branches (HTTP error paths, cache
no-op flush, multi-filter combinations, link --url branch, verify-signature
key precedence). Coverage gate requires =>=95%.

## Solution
Added the missing test cases. coverage report --fail-under=95 now passes.

## Verified
coverage run -m unittest discover tests; coverage report --fail-under=95
returns exit 0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 6 — Final integration smoke

### Task 30: End-to-end manual smoke (live API)

This task is run by a human (or an agent with permission to call the live API). It verifies the wire-level migration works against real Kanban Zone, not just mocked.

- [ ] **Step 1: Confirm `.env` has a valid `KANBAN_ZONE_API_KEY` and `KANBAN_ZONE_BOARD_ID` for a non-production board.**

- [ ] **Step 2: Run the read-only smoke battery.**

```bash
python3 scripts/kanban_zone_api.py org me
python3 scripts/kanban_zone_api.py boards list
python3 scripts/kanban_zone_api.py boards get --include-columns
python3 scripts/kanban_zone_api.py cards list --count 5
python3 scripts/kanban_zone_api.py reports throughput --from-date 2026-01-01 --to-date 2026-04-01
```
Expected: each command exits 0 and prints valid JSON.

- [ ] **Step 3: Run the round-trip write smoke (creates and deletes a card).**

```bash
CREATE=$(python3 scripts/kanban_zone_api.py cards create --title "v3 smoke test")
NUM=$(echo "$CREATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['cards'][0]['number'])")
python3 scripts/kanban_zone_api.py cards update --id "$NUM" --description "round-trip"
python3 scripts/kanban_zone_api.py comments add --card "$NUM" --text "smoke"
python3 scripts/kanban_zone_api.py cards delete --id "$NUM"
```
Expected: each command exits 0; final delete returns `{"deleted": true, ...}`.

- [ ] **Step 4: Run the legacy alias smoke.**

```bash
python3 scripts/kanban_zone_api.py boards
python3 scripts/kanban_zone_api.py cards --label "Bug" 2>/dev/null || true
```
Expected: both still work and return JSON.

- [ ] **Step 5: Tag the release.**

```bash
git tag -a v3.0.0 -m "v3.0.0 — API v1.4 coverage, grouped CLI, =>=95% coverage"
```

(Pushing the tag is left to the human; the agent should not push without explicit approval.)

---

## Self-review checklist

After executing the full plan, verify the spec acceptance criteria from `docs/superpowers/specs/2026-05-10-kanban-zone-skill-v3-design.md` §11:

1. Every endpoint in spec §3.2 is reachable through the grouped CLI surface — covered by Tasks 9-19.
2. Every command in spec §4.2 still works as a hidden alias — covered by Task 20 + Task 21 integration smoke.
3. Bidirectional cache exercised — covered by `tests/test_cache.py` (Task 6) and `tests/test_ids.py` (Task 7).
4. Webhook signature helper exit codes — covered by `tests/test_webhooks.py` (Task 18).
5. `coverage report --fail-under=95` succeeds — Task 29.
6. Docs: SKILL.md/README.md/AGENTS.md/api-reference.md/migration-from-v2.md/CHANGELOG.md all reflect v3.0.0 content — Tasks 22-28.
7. SKILL.md and AGENTS.md sync clauses present — Tasks 22 and 24.

If any criterion is unsatisfied, add a follow-up task at the end of the plan and resume the implementation loop.


