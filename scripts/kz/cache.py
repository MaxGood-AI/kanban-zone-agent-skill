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
