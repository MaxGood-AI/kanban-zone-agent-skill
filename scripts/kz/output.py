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
