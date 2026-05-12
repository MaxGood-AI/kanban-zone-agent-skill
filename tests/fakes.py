"""Test fakes for the kanban_zone package — primarily the FakeApi context manager."""
import sys
from dataclasses import dataclass, field
from typing import Any, List, Optional

sys.path.insert(0, "scripts")
from kanban_zone import http as kanban_zone_http


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
    """Context manager that monkey-patches kanban_zone.http.api_request with a queue."""

    def __init__(self):
        self.expectations: List[_Expectation] = []
        self.calls: List[_Call] = []
        self._original = None

    def __enter__(self):
        self._original = kanban_zone_http.api_request
        kanban_zone_http.api_request = self._intercept
        return self

    def __exit__(self, exc_type, exc, tb):
        kanban_zone_http.api_request = self._original

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
