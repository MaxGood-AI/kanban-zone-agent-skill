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
