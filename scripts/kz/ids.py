"""Card identifier resolution.

Auto-detects card numbers (pure digits) vs ObjectIds (24-hex).
Resolves either direction through the agent cache, falling back to API calls.
"""
import re

from kz import http as kz_http


def _unwrap_card(card):
    """Return a flat card dict, handling the v1.4 {"_id": ..., "CardItem": {...}} envelope.

    Duplicated from kz.cards to avoid a circular import (cards imports ids).
    """
    if not isinstance(card, dict):
        return card
    inner = card.get("CardItem")
    if isinstance(inner, dict):
        flat = dict(inner)
        if "_id" in card and "_id" not in flat:
            flat["_id"] = card["_id"]
        return flat
    return card


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
        for raw_card in (resp or {}).get("cards", []):
            card = _unwrap_card(raw_card)
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
    number = _unwrap_card(resp or {}).get("number")
    if number is None:
        raise KZIdError(f"Card {value} returned no number field")
    cache.set_card_mapping(board, number, value)
    return int(number)
