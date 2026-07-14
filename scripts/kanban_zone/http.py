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

SKILL_VERSION = "3.2.0"
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


class KanbanZoneUsageLimitError(KanbanZoneApiError):
    """The organization's monthly API usage limit is exhausted.

    Kanban Zone reports this as **HTTP 200** with the error only inside the
    body (``{"code": 2006, "status": 429, "name": "TooManyRequests",
    "message": "API Usage limit reached"}``), so without detection it
    masquerades as a successful-but-empty response — e.g. a card-number
    lookup "scanning 0 cards" and concluding the card does not exist.

    Subclasses :class:`KanbanZoneApiError` so the CLI's top-level handler
    catches it like any other API error. Carries a complete, actionable
    message meant to be shown verbatim to a human or an AI agent.
    """

    def __init__(self, message, request_line):
        # Bypass KanbanZoneApiError's terse "<line> -> HTTP <n>: <body>"
        # formatting — `message` is already a full, self-contained explanation.
        Exception.__init__(self, message)
        self.status = 429
        self.body = message
        self.request_line = request_line


# Shown verbatim when the monthly usage limit is hit. Written to be useful to
# both humans and AI agents: it states the outcome, the cause, that retrying
# is futile, and where the human can verify usage.
_USAGE_LIMIT_MESSAGE = (
    "This request was REJECTED: the Kanban Zone organization has reached its "
    "monthly API usage limit (Kanban Zone error code 2006, 'API Usage limit "
    "reached'). Kanban Zone returns this as HTTP 200 with the error only in "
    "the response body, so without this check it would look like an empty "
    "result instead of an error. NO API call will succeed until the monthly "
    "quota resets or the plan's limit is raised — do NOT retry. Ask the user "
    "to open Kanban Zone's web interface and check the Organization > "
    "Integrations panel (https://kanbanzone.io/settings/integrations), where "
    "the 'Available API Calls' meter shows current usage against the plan's "
    "monthly limit."
)


def _raise_on_error_envelope(parsed, request_line):
    """Raise if a 2xx response body is actually a Kanban Zone error envelope.

    Kanban Zone's API edge sometimes delivers errors with an HTTP 200 status
    code, leaving the real error only in the JSON body (the same pathology as
    the DELETE "Body Parser failed" bug). Recognized shapes:

    - ``code == 2006`` or ``name == "TooManyRequests"`` — the monthly usage
      limit; raised as :class:`KanbanZoneUsageLimitError`.
    - a numeric ``status`` >= 400 alongside ``name`` and ``message`` keys —
      any other hidden error envelope; raised as :class:`KanbanZoneApiError`
      with the body's status. All three keys are required so genuine resource
      payloads that happen to contain a ``status`` field are never mistaken
      for an error.
    """
    if not isinstance(parsed, dict):
        return
    if parsed.get("code") == 2006 or parsed.get("name") == "TooManyRequests":
        raise KanbanZoneUsageLimitError(_USAGE_LIMIT_MESSAGE, request_line)
    body_status = parsed.get("status")
    if (
        isinstance(body_status, int)
        and body_status >= 400
        and "name" in parsed
        and "message" in parsed
    ):
        raise KanbanZoneApiError(body_status, json.dumps(parsed), request_line)


def api_request(method, path, params=None, body=None):
    """Send an HTTP request to the Kanban Zone API and return parsed JSON.

    Returns None on 204. Raises KanbanZoneApiError on non-2xx,
    KanbanZoneAuthError on missing key, and KanbanZoneUsageLimitError (or
    KanbanZoneApiError) when a 2xx body carries a hidden error envelope —
    Kanban Zone reports some errors, e.g. the monthly usage limit, with
    HTTP 200.
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
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise KanbanZoneApiError(
            status, f"non-JSON response: {raw[:200]!r}", request_line
        ) from exc
    _raise_on_error_envelope(parsed, request_line)
    return parsed


class KanbanZoneDeleteUnsupportedError(KanbanZoneApiError):
    """A DELETE was rejected with Kanban Zone's "Body Parser failed" envelope
    (see :func:`delete_resource`).

    Historically (2026-05-16 through 2026-06-11) every Kanban Zone DELETE
    failed this way server-side. Kanban Zone has since fixed its API; this
    error remains as a regression guard so a returning defect fails loudly
    instead of being reported as a fake success.

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
    "This {resource} was NOT deleted. Kanban Zone rejected the DELETE with a "
    '"Body Parser failed" error (returned, misleadingly, as HTTP 200). This '
    "matches a Kanban Zone server-side defect that broke every DELETE "
    "endpoint from 2026-05-16 until Kanban Zone fixed it on 2026-06-11 — if "
    "you are seeing this, the defect has likely regressed, and retrying will "
    "not help. Delete this {resource} via the Kanban Zone web UI instead, "
    "and tell the user so the regression can be reported to Kanban Zone. "
    "See the kanban-zone skill README."
)


def delete_resource(resource, path, params=None):
    """Issue a DELETE for a single resource and interpret Kanban Zone's reply.

    ``resource`` is a human-readable noun ("card", "checklist", "task",
    "webhook", "token") used in error messages. Returns the parsed response
    (``None`` for a real HTTP 204) on success.

    Kanban Zone's DELETE endpoints were broken server-side from 2026-05-16
    to 2026-06-11: they answered HTTP 200 with a
    ``{"message": "Body Parser failed ..."}`` envelope and never deleted the
    record (the AWS edge stripped DELETE request bodies). Kanban Zone fixed
    that, but the detection stays as a regression guard: if the envelope
    reappears this raises :class:`KanbanZoneDeleteUnsupportedError` with an
    actionable message; any other 200 error envelope is surfaced as a plain
    :class:`KanbanZoneApiError`. A genuine resource object (which carries
    ``_id``) is returned untouched.
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
