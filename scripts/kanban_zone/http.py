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

SKILL_VERSION = "3.1.2"
BASE_URL = "https://integrations.kanbanzone.io/v1"

_cached_auth_header = None


class KanbanZoneApiError(Exception):
    def __init__(self, status, body, request_line):
        super().__init__(f"{request_line} -> HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body
        self.request_line = request_line


class KanbanZoneAuthError(Exception):
    pass


def _auth_header():
    global _cached_auth_header
    if _cached_auth_header is not None:
        return _cached_auth_header
    raw = os.environ.get("KANBAN_ZONE_API_KEY") or ""
    raw = raw.strip()
    if not raw:
        raise KanbanZoneAuthError(
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

    Returns None on 204. Raises KanbanZoneApiError on non-2xx, KanbanZoneAuthError on missing key.
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
        raise KanbanZoneApiError(exc.code, raw.decode("utf-8", errors="replace"), request_line)
    except urllib.error.URLError as exc:
        raise KanbanZoneApiError(0, str(exc.reason), request_line)

    if status == 204 or not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise KanbanZoneApiError(
            status, f"non-JSON response: {raw[:200]!r}", request_line
        ) from exc


class KanbanZoneDeleteUnsupportedError(KanbanZoneApiError):
    """A DELETE failed because Kanban Zone's DELETE endpoints are non-functional
    server-side (see :func:`delete_resource`).

    Subclasses :class:`KanbanZoneApiError` so the CLI's top-level handler
    catches it like any other API error. Carries a complete, actionable
    message meant to be shown verbatim to a human or an AI agent.
    """

    def __init__(self, message, request_line):
        # Bypass KanbanZoneApiError's terse "<line> -> HTTP <n>: <body>"
        # formatting — `message` is already a full, self-contained explanation.
        Exception.__init__(self, message)
        self.status = None
        self.body = message
        self.request_line = request_line


# Shown verbatim when a delete fails. Written to be useful to both humans and
# AI agents: it states the outcome, the cause, that retrying is futile, and
# the concrete workaround. ``{resource}`` is filled with "card"/"task"/etc.
_DELETE_BUG_MESSAGE = (
    "This {resource} was NOT deleted. Kanban Zone's DELETE API is currently "
    "non-functional: this is a known Kanban Zone server-side bug, not a "
    "problem with your request or this skill, and retrying will not help. "
    "Kanban Zone's API edge strips the body from DELETE requests, so its "
    'DELETE routes reject every call with "Body Parser failed" (returned, '
    "misleadingly, as HTTP 200). To delete this {resource}, use the "
    "Kanban Zone web UI instead. All DELETE endpoints (cards, checklists, "
    "tasks, webhooks, tokens) are affected. Reported to Kanban Zone "
    "2026-05-16; see the kanban-zone skill README."
)


def delete_resource(resource, path, params=None):
    """Issue a DELETE for a single resource and interpret Kanban Zone's reply.

    ``resource`` is a human-readable noun ("card", "checklist", "task",
    "webhook", "token") used in error messages. Returns the parsed response
    (``None`` for a real HTTP 204) on success.

    Kanban Zone's DELETE endpoints are currently broken server-side: they
    answer HTTP 200 with a ``{"message": "Body Parser failed ..."}`` envelope
    and never delete the record (its AWS edge strips DELETE request bodies).
    When that is detected this raises :class:`KanbanZoneDeleteUnsupportedError`
    with an actionable message; any other 200 error envelope is surfaced as a
    plain :class:`KanbanZoneApiError`. A genuine resource object (which
    carries ``_id``) is returned untouched.
    """
    resp = api_request("DELETE", path, params=params, body={})
    if isinstance(resp, dict) and "message" in resp and "_id" not in resp:
        request_line = f"DELETE {path}"
        if "body parser" in str(resp.get("message", "")).lower():
            raise KanbanZoneDeleteUnsupportedError(
                _DELETE_BUG_MESSAGE.format(resource=resource), request_line
            )
        raise KanbanZoneApiError(200, json.dumps(resp), request_line)
    return resp
